import os
import threading
from PySide6.QtCore import QObject, Signal
import time

class ModelLoader(QObject):
    """模型加载器，负责加载模型并报告进度"""
    
    # 定义信号
    loading_progress = Signal(str, float)  # 模型名称，加载进度
    loading_complete = Signal(str)  # 模型名称
    loading_error = Signal(str, str)  # 模型名称，错误信息
    all_models_loaded = Signal()  # 所有模型加载完成信号
    
    def __init__(self, model_manager):
        super().__init__()
        self.model_manager = model_manager
        self.loading_tasks = {}
        self.loaded_models = {}
    
    def load_models(self):
        """加载所有检测到的模型"""
        # 获取各类型的模型路径
        llm_path = self.model_manager.get_model_path(self.model_manager.MODEL_TYPE_LLM)
        embedding_path = self.model_manager.get_model_path(self.model_manager.MODEL_TYPE_EMBEDDING)
        
        # 检测所有可用模型
        llm_models = self.model_manager.detect_models(llm_path, self.model_manager.MODEL_TYPE_LLM)
        embedding_models = self.model_manager.detect_models(embedding_path, self.model_manager.MODEL_TYPE_EMBEDDING)
        
        # 计算要加载的模型数量
        self.models_to_load = len(llm_models) + len(embedding_models)
        if self.models_to_load == 0:
            # 没有可用模型
            self.all_models_loaded.emit()
            return
        
        # 设置计数器
        self.models_loaded = 0
        
        # 开始加载模型
        for model in llm_models:
            print(f"开始加载LLM模型: {model['name']}")
            self._load_llm_model(model)
        
        for model in embedding_models:
            print(f"开始加载向量模型: {model['name']}")
            self._load_embedding_model(model)
        
    def _load_model_task(self, model_info, model_type):
        """加载单个模型的任务"""
        try:
            model_name = model_info.get("name", "未命名模型")
            model_path = model_info.get("path", "")
            
            # 标准化路径
            model_path = self.model_manager.normalize_model_path(model_path)
            model_info["path"] = model_path
            
            # 发出加载开始信号
            self.loading_progress.emit(model_name, 0.0)
            
            # 根据模型类型选择加载方法
            if model_type == self.model_manager.MODEL_TYPE_LLM:
                self._load_llm_model(model_info)
            elif model_type == self.model_manager.MODEL_TYPE_EMBEDDING:
                self._load_embedding_model(model_info)
            
            # 保存已加载的模型信息
            self.loaded_models[model_type] = model_info
            
            # 发出加载完成信号
            self.loading_progress.emit(model_name, 1.0)
            self.loading_complete.emit(model_name)
            
            # 增加已加载计数
            self.models_loaded += 1
            
            # 检查是否所有模型都已经加载完成
            self._check_all_loaded()
            
        except Exception as e:
            # 发出加载错误信号
            self.loading_error.emit(model_name, str(e))
            
            # 增加已加载计数（虽然失败）
            self.models_loaded += 1
            
            # 检查是否所有模型都已经加载完成
            self._check_all_loaded()
        
        # 清理加载任务
        if model_name in self.loading_tasks:
            del self.loading_tasks[model_name]
    
    def _load_llm_model(self, model_info):
        """加载对话模型"""
        model_path = model_info["path"]
        
        # 标准化路径
        model_path = self.model_manager.normalize_model_path(model_path)
        model_info["path"] = model_path
        
        print(f"准备加载LLM模型: {model_path}")
        # 实际加载代码...
    
    def _load_embedding_model(self, model_info):
        """加载向量模型并同步到术语向量数据库"""
        def load_thread():
            try:
                model_path = model_info["path"]
                model_name = model_info["name"]
                print(f"加载向量模型: {model_path}")
                
                # 发出加载进度信号
                self.loading_progress.emit(model_name, 0.1)
                
                # 检查模型文件完整性
                if "bge-m3" in model_path.lower():
                    if not self.model_manager.check_model_files(model_path, self.model_manager.MODEL_TYPE_EMBEDDING):
                        print("BGE-M3模型文件不完整，尝试修复...")
                        self.loading_progress.emit(model_name, 0.2)
                        
                        # 修复模型
                        if self.model_manager.repair_model(model_path, self.model_manager.MODEL_TYPE_EMBEDDING):
                            print("BGE-M3模型修复完成")
                            # 更新模型路径
                            expected_path = os.path.join("BAAI", "models", "BAAI", "bge-m3")
                            if os.path.exists(expected_path):
                                model_path = expected_path
                                model_info["path"] = expected_path
                                print(f"更新BGE-M3模型路径为: {expected_path}")
                        else:
                            print("BGE-M3模型修复失败")
                            raise Exception("模型文件损坏，无法加载")
                
                # 检查BGE-M3下载状态
                if "bge-m3" in model_path.lower():
                    # 检查下载目录
                    expected_path = os.path.join("BAAI", "models", "BAAI", "bge-m3")
                    if not os.path.exists(expected_path):
                        self.loading_progress.emit(model_name, 0.2)
                        print(f"BGE-M3模型正在下载中，请等待下载完成...")
                        # 等待下载完成的逻辑
                        for i in range(10):
                            time.sleep(2)  # 每2秒检查一次
                            if os.path.exists(expected_path):
                                print(f"检测到BGE-M3模型已下载完成")
                                break
                            self.loading_progress.emit(model_name, 0.2 + i * 0.05)
                        
                        # 更新模型路径
                        if os.path.exists(expected_path):
                            model_path = expected_path
                            model_info["path"] = expected_path
                            print(f"更新BGE-M3模型路径为: {expected_path}")
                
                # 模拟更多加载进度
                self.loading_progress.emit(model_name, 0.6)
                
                # 保存模型信息到model_loader
                self.loaded_models[self.model_manager.MODEL_TYPE_EMBEDDING] = model_info
                
                # 加载完成
                self.loading_progress.emit(model_name, 1.0)
                self.loading_complete.emit(model_name)
                
                # 加载模型成功后，同步到术语向量数据库
                if hasattr(self.model_manager, 'assistant'):
                    assistant = self.model_manager.assistant
                    if (hasattr(assistant, 'term_vector_db') and
                        hasattr(assistant, 'vector_db') and
                        assistant.vector_db.model):
                        # 复用同一个模型实例
                        assistant.term_vector_db.model = assistant.vector_db.model
                        print("已同步向量模型到术语向量数据库")
            except Exception as e:
                print(f"加载向量模型失败: {e}")
                import traceback
                traceback.print_exc()
                self.loading_error.emit(model_info["name"], str(e))
        
        # 启动加载线程
        thread = threading.Thread(target=load_thread)
        thread.daemon = True
        thread.start()
        self.loading_tasks[model_info["name"]] = thread
    
    def _check_all_loaded(self):
        """检查是否所有模型都已加载完成"""
        if self.models_loaded >= self.models_to_load:
            self.all_models_loaded.emit()
    
    def get_loaded_model(self, model_type):
        """获取已加载的特定类型模型信息"""
        return self.loaded_models.get(model_type) 