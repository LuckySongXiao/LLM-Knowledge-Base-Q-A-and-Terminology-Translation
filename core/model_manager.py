import os
import sys
import shutil
import requests
import json
import torch
import psutil
import threading
from PySide6.QtCore import QObject, Signal
from tqdm import tqdm

class ModelManager(QObject):
    """模型管理器，负责检测和下载模型"""
    
    # 定义信号
    download_progress = Signal(str, float)  # 模型名称，下载进度
    download_complete = Signal(str)  # 模型名称
    download_error = Signal(str, str)  # 模型名称，错误信息
    
    # 模型类型
    MODEL_TYPE_LLM = "llm"          # 大语言模型
    MODEL_TYPE_EMBEDDING = "embedding"  # 向量模型
    
    # 默认模型信息 - 使用魔塔社区模型ID
    DEFAULT_MODELS = {
        MODEL_TYPE_LLM: {
            "id": "qwen2.5-3b-instruct",
            "name": "通义千问2.5-3B指令版",
            "description": "阿里巴巴的通义千问2.5-3B指令模型",
            "model_file": "model.safetensors"
        },
        MODEL_TYPE_EMBEDDING: {
            "id": "bge-m3",
            "name": "BGE-M3向量模型",
            "description": "清华大学发布的多语言向量模型",
            "model_file": "model.safetensors"
        }
    }
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.models_info = {}  # 存储可用模型信息
        self.download_tasks = {}  # 当前下载任务
        
    def set_model_path(self, path, model_type=MODEL_TYPE_LLM):
        """设置模型路径并检测模型"""
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            
        if model_type == self.MODEL_TYPE_LLM:
            self.settings.set('model_path', path)
        elif model_type == self.MODEL_TYPE_EMBEDDING:
            self.settings.set('vector_model_path', path)
            
        return self.detect_models(path, model_type)
    
    def get_model_path(self, model_type):
        """获取指定类型模型的路径"""
        if model_type == self.MODEL_TYPE_LLM:
            return self.settings.get('model_path', '')
        elif model_type == self.MODEL_TYPE_EMBEDDING:
            return self.settings.get('vector_model_path', '')
        return ''
    
    def detect_models(self, path, model_type=MODEL_TYPE_LLM):
        """检测指定路径下的模型文件"""
        available_models = []
        
        if not os.path.exists(path):
            return available_models
            
        # 打印调试信息
        print(f"扫描路径: {path} 查找 {model_type} 类型模型")
        
        # 检查路径是否直接是Qwen2模型文件夹
        if os.path.isdir(path) and model_type == self.MODEL_TYPE_LLM:
            # 检查当前目录
            if os.path.exists(os.path.join(path, "config.json")) and os.path.exists(os.path.join(path, "model.safetensors")):
                model_name = os.path.basename(path)
                available_models.append({
                    "name": model_name,
                    "path": path,
                    "type": "transformer",
                    "size": self._get_dir_size(path) / (1024 * 1024 * 1024)  # GB
                })
                print(f"检测到模型: {model_name}")
                return available_models
                
            # 检查子目录
            for subdir in os.listdir(path):
                subdir_path = os.path.join(path, subdir)
                if os.path.isdir(subdir_path):
                    if os.path.exists(os.path.join(subdir_path, "config.json")) and os.path.exists(os.path.join(subdir_path, "model.safetensors")):
                        model_name = subdir
                        available_models.append({
                            "name": model_name,
                            "path": subdir_path,
                            "type": "transformer",
                            "size": self._get_dir_size(subdir_path) / (1024 * 1024 * 1024)  # GB
                        })
                        print(f"检测到模型: {model_name}")
                        return available_models
        
        if model_type == self.MODEL_TYPE_LLM:
            # 检测GGUF格式模型
            gguf_files = [f for f in os.listdir(path) if f.endswith('.gguf')]
            for file in gguf_files:
                model_name = os.path.splitext(file)[0]
                available_models.append({
                    "name": model_name,
                    "path": os.path.join(path, file),
                    "type": "gguf",
                    "size": os.path.getsize(os.path.join(path, file)) / (1024 * 1024 * 1024)  # GB
                })
                
            # 检测其他LLM格式
            # 检测safetensors目录
            for dir_name in os.listdir(path):
                dir_path = os.path.join(path, dir_name)
                if os.path.isdir(dir_path):
                    # 检查是否包含模型文件
                    if any(f.endswith('.safetensors') for f in os.listdir(dir_path)):
                        available_models.append({
                            "name": dir_name,
                            "path": dir_path,
                            "type": "safetensors",
                            "size": self._get_dir_size(dir_path) / (1024 * 1024 * 1024)  # GB
                        })
                    # 也检查pytorch格式
                    elif any(f.endswith('.bin') for f in os.listdir(dir_path)):
                        available_models.append({
                            "name": dir_name,
                            "path": dir_path,
                            "type": "pytorch",
                            "size": self._get_dir_size(dir_path) / (1024 * 1024 * 1024)  # GB
                        })
                    # 检查tokenizer配置
                    elif os.path.exists(os.path.join(dir_path, "tokenizer.json")) or \
                         os.path.exists(os.path.join(dir_path, "tokenizer_config.json")):
                        available_models.append({
                            "name": dir_name,
                            "path": dir_path,
                            "type": "transformer",
                            "size": self._get_dir_size(dir_path) / (1024 * 1024 * 1024)  # GB
                        })
                    
        elif model_type == self.MODEL_TYPE_EMBEDDING:
            # 检测向量模型
            for dir_name in os.listdir(path):
                dir_path = os.path.join(path, dir_name)
                if os.path.isdir(dir_path):
                    # 检查是否是embedding模型
                    if os.path.exists(os.path.join(dir_path, "config.json")) or \
                       os.path.exists(os.path.join(dir_path, "sentence_bert_config.json")) or \
                       any(f.endswith('.bin') and "embed" in f.lower() for f in os.listdir(dir_path)):
                        available_models.append({
                            "name": dir_name,
                            "path": dir_path,
                            "type": "embedding",
                            "size": self._get_dir_size(dir_path) / (1024 * 1024 * 1024)  # GB
                        })
                
        return available_models
    
    def _get_dir_size(self, path):
        """获取目录大小（字节）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    
    def check_hardware(self):
        """检测系统硬件"""
        hardware_info = {}
        
        # 检测GPU
        hardware_info["has_gpu"] = torch.cuda.is_available()
        if hardware_info["has_gpu"]:
            hardware_info["gpu_name"] = torch.cuda.get_device_name(0)
            hardware_info["gpu_memory"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        else:
            hardware_info["gpu_name"] = None
            hardware_info["gpu_memory"] = 0
        
        # 检测系统内存
        hardware_info["system_memory"] = psutil.virtual_memory().total / (1024**3)  # GB
        
        # CPU信息
        hardware_info["cpu_count"] = psutil.cpu_count(logical=True)
        
        return hardware_info
    
    def get_recommended_models(self, model_type=MODEL_TYPE_LLM):
        """根据硬件情况获取推荐模型"""
        hardware = self.check_hardware()
        recommended = []
        
        # 从魔塔社区API获取模型列表
        try:
            # 修改为魔塔社区API
            response = requests.get("https://api.modelscope.cn/v1/models", 
                                   params={"Domain": self._get_domain_for_type(model_type)})
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "models" in data["data"]:
                    model_list = data["data"]["models"]
                    # 处理魔塔社区返回的模型列表
                    for model in model_list:
                        model_info = {
                            "id": model.get("Id", ""),
                            "name": model.get("Name", "未命名模型"),
                            "description": model.get("Description", ""),
                            "model_id": model.get("ModelId", ""),
                            "required_gpu_memory": 8,  # 默认值，实际应从API获取
                            "required_memory": 16,     # 默认值，实际应从API获取
                            "cpu_compatible": True,    # 默认值，实际应从API获取
                            "download_url": f"https://modelscope.cn/models/{model.get('ModelId', '')}/summary",
                            "model_type": model_type,
                            "tags": model.get("Tags", [])
                        }
                        self.models_info.append(model_info)
                else:
                    self.models_info = self._get_default_models(model_type)
            else:
                self.models_info = self._get_default_models(model_type)
        except Exception:
            self.models_info = self._get_default_models(model_type)
        
        # 根据硬件筛选模型
        for model in self.models_info:
            if model_type != model.get("model_type", self.MODEL_TYPE_LLM):
                continue
                
            if hardware["has_gpu"]:
                # GPU模式下的推荐
                if model["required_gpu_memory"] <= hardware["gpu_memory"]:
                    recommended.append(model)
            else:
                # CPU模式下的推荐
                if model.get("cpu_compatible", False) and model["required_memory"] <= hardware["system_memory"]:
                    recommended.append(model)
        
        # 如果没有推荐模型，至少返回默认模型
        if not recommended and model_type in self.DEFAULT_MODELS:
            recommended.append(self.DEFAULT_MODELS[model_type])
            
        return recommended
    
    def _get_domain_for_type(self, model_type):
        """获取模型类型对应的领域分类"""
        if model_type == self.MODEL_TYPE_LLM:
            return "nlp"
        elif model_type == self.MODEL_TYPE_EMBEDDING:
            return "nlp"
        return "nlp"
    
    def _get_default_models(self, model_type=None):
        """获取默认模型列表"""
        if model_type:
            return [self.DEFAULT_MODELS.get(model_type, self.DEFAULT_MODELS[self.MODEL_TYPE_LLM])]
        else:
            return list(self.DEFAULT_MODELS.values())
    
    def check_and_download_default_models(self):
        """检查并下载默认模型"""
        # 获取项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 检查对话模型
        llm_path = os.path.join(base_dir, "QWEN")
        self.settings.set('model_path', llm_path)
        llm_models = self.detect_models(llm_path, self.MODEL_TYPE_LLM)
        if not llm_models:
            print(f"未检测到QWEN模型，将下载默认模型: 千问2.5-3B")
            self.download_model_from_modelscope(
                self.DEFAULT_MODELS[self.MODEL_TYPE_LLM]["id"],
                "QWEN"
            )
        
        # 检查向量模型
        vector_path = os.path.join(base_dir, "BAAI")  # 修改为项目内部路径
        self.settings.set('vector_model_path', vector_path)
        vector_models = self.detect_models(vector_path, self.MODEL_TYPE_EMBEDDING)
        if not vector_models:
            print(f"未检测到BAAI模型，将下载默认模型: BGE-M3")
            self.download_model_from_modelscope(
                self.DEFAULT_MODELS[self.MODEL_TYPE_EMBEDDING]["id"],
                "BAAI",
                base_dir  # 传入基础目录以确保下载到正确位置
            )
    
    def download_model(self, model_id, model_type=MODEL_TYPE_LLM):
        """下载指定模型"""
        # 查找模型信息
        model_info = None
        
        # 首先检查默认模型
        if model_type in self.DEFAULT_MODELS and self.DEFAULT_MODELS[model_type]["id"] == model_id:
            model_info = self.DEFAULT_MODELS[model_type]
        else:
            # 然后检查API获取的模型
            for model in self.models_info:
                if model["id"] == model_id:
                    model_info = model
                    break
        
        if not model_info:
            self.download_error.emit(model_id, "找不到指定模型信息")
            return False
        
        # 创建下载任务
        task = threading.Thread(
            target=self._download_model_task,
            args=(model_info, model_type)
        )
        task.daemon = True
        self.download_tasks[model_id] = task
        task.start()
        
        return True
    
    def _download_model_task(self, model_info, model_type):
        """下载模型的任务函数"""
        try:
            from modelscope.hub.snapshot_download import snapshot_download
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(model_info["path"]), exist_ok=True)
            
            # 实际下载 - 移除不支持的参数
            print(f"开始从魔塔社区下载模型: {model_info['id']} 到 {model_info['path']}")
            
            # 移除不支持的progress参数
            snapshot_download(
                model_id=model_info["id"],
                cache_dir=model_info["path"]
                # 移除progress参数
            )
            
            print(f"模型 {model_info['id']} 下载完成")
            self.download_complete.emit(model_info["id"])
            return True
        except Exception as e:
            print(f"下载模型时出错: {e}")
            import traceback
            traceback.print_exc()
            self.download_error.emit(model_info["id"], str(e))
            return False
    
    def cancel_download(self, model_id):
        """取消下载任务"""
        if model_id in self.download_tasks:
            # 注意: Python线程无法直接强制终止
            # 这里只是从任务列表中移除，实际下载可能会继续
            del self.download_tasks[model_id]
            return True
        return False
    
    def normalize_model_path(self, path):
        """处理路径中的特殊字符问题"""
        # 处理路径中的"___"等特殊字符
        if "___" in path:
            print(f"检测到路径中有特殊字符: {path}")
            # 尝试获取真实目录名
            if os.path.exists(os.path.dirname(path)):
                parent_dir = os.path.dirname(path)
                base_name = os.path.basename(path)
                # 查找相似目录名
                for dir_name in os.listdir(parent_dir):
                    if dir_name.replace("___", "-") == base_name.replace("___", "-"):
                        normalized_path = os.path.join(parent_dir, dir_name)
                        print(f"找到匹配目录，标准化路径为: {normalized_path}")
                        return normalized_path
        return path

    def check_model_files(self, model_path, model_type):
        """检查模型文件是否完整"""
        if model_type == self.MODEL_TYPE_EMBEDDING and "bge-m3" in model_path.lower():
            # 检查BGE-M3模型文件
            required_files = ["pytorch_model.bin", "config.json", "tokenizer_config.json"]
            for file in required_files:
                file_path = os.path.join(model_path, file)
                if not os.path.exists(file_path):
                    print(f"警告: 找不到必要的模型文件: {file_path}")
                    return False
                
            # 检查pytorch_model.bin的大小，确保下载完整
            model_bin = os.path.join(model_path, "pytorch_model.bin")
            expected_size = 250000000  # 大约250MB
            actual_size = os.path.getsize(model_bin)
            if actual_size < expected_size * 0.9:  # 允许有10%的差异
                print(f"警告: 模型文件大小异常: {model_bin}")
                print(f"实际大小: {actual_size/1000000:.2f}MB, 预期大小: {expected_size/1000000:.2f}MB")
                return False
            
        return True

    def repair_model(self, model_path, model_type):
        """尝试修复模型问题"""
        if model_type == self.MODEL_TYPE_EMBEDDING and "bge-m3" in model_path.lower():
            print(f"尝试修复BGE-M3模型: {model_path}")
            
            # 删除可能损坏的模型目录
            import shutil
            if os.path.exists(model_path):
                try:
                    shutil.rmtree(model_path)
                    print(f"已删除损坏的模型目录: {model_path}")
                except Exception as e:
                    print(f"删除模型目录失败: {e}")
            
            # 重新下载模型
            print("重新下载BGE-M3模型...")
            self.download_model_from_modelscope(self.DEFAULT_MODELS[self.MODEL_TYPE_EMBEDDING]["id"], "BAAI")
            return True
        
        return False

    def download_model_from_modelscope(self, model_id, target_folder, base_dir=None):
        """从ModelScope下载模型"""
        try:
            from modelscope.hub.snapshot_download import snapshot_download
            
            # 确定基础目录
            if base_dir is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 构建目标目录
            target_dir = os.path.join(base_dir, target_folder, "models", model_id)
            display_name = model_id.split('/')[-1]
            
            print(f"开始从魔塔社区下载模型: {model_id}")
            print(f"下载到目录: {target_dir}")
            
            # 创建目标目录
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            
            # 下载模型 - 修复方法名错误
            task = threading.Thread(
                target=self._download_model_task,  # 修正为正确的方法名
                args=(model_id, target_dir, display_name)
            )
            task.daemon = True
            self.download_tasks[model_id] = task
            task.start()
            
            return True
        except Exception as e:
            print(f"从魔塔社区下载失败: {e}")
            import traceback
            traceback.print_exc()
            self.download_error.emit(model_id, str(e))
            return False 