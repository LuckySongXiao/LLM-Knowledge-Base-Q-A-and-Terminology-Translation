import os
import threading
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
from .model_quantizer import ModelQuantizer

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseEngine:
    """AI基础引擎，提供所有子引擎共享的功能"""
    
    def __init__(self, settings):
        """初始化基础引擎"""
        try:
            # 保存设置
            self.settings = settings
            
            # 获取模型路径
            model_path = settings.get('model_path', 'QWEN')
            self.model_path = model_path
            
            # 初始化模型和tokenizer
            self.model = None
            self.tokenizer = None
            self.gguf_model = None  # GGUF模型
            
            # 初始化model_type和device属性
            self.model_type = "未知模型"
            self.device = "未知设备"
            
            # 创建量化管理器
            self.quantizer = ModelQuantizer(settings)
            logger.info(f"初始化量化管理器完成，自动选择量化级别: {self.quantizer.auto_level.name}")
            
            # 生成配置 - 通用配置，子类可以覆盖
            self.generation_config = {
                "max_new_tokens": 1024,  # 最大生成长度
                "temperature": 0.6,      # 温度参数
                "top_p": 0.6,            # top-p采样
                "top_k": 15,             # top-k采样
                "repetition_penalty": 1.3,  # 重复惩罚
                "do_sample": False       # 使用贪婪解码
            }
            
            # 从设置中读取温度参数
            temperature = float(settings.get('temperature', 0.6))
            self.generation_config["temperature"] = temperature
            
            logger.info(f"初始化基础引擎完成，温度参数: {temperature}")
        except Exception as e:
            logger.error(f"基础引擎初始化失败: {e}")
        
        # 设置设备，优先使用CUDA
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"基础引擎使用设备: {self.device}")
        
        self._lock = threading.Lock()
        
    def load_models(self):
        """加载AI模型"""
        if self.model_path and not self.model:
            print(f"准备加载LLM模型: {self.model_path}")
            
            # 检查模型路径是否为目录而非具体模型
            if os.path.isdir(self.model_path) and not os.path.exists(os.path.join(self.model_path, "config.json")):
                # 如果是目录且没有config.json，尝试查找子目录中的模型
                model_dirs = [d for d in os.listdir(self.model_path) 
                             if os.path.isdir(os.path.join(self.model_path, d)) and 
                             os.path.exists(os.path.join(self.model_path, d, "config.json"))]
                
                if model_dirs:
                    # 使用找到的第一个有效模型路径
                    model_subdir = model_dirs[0]
                    print(f"找到有效模型子目录: {model_subdir}")
                    self.model_path = os.path.join(self.model_path, model_subdir)
                else:
                    print(f"错误: 在 {self.model_path} 中未找到有效的模型文件")
                    return False
            
            # 根据模型类型选择加载方法
            if self.model_type == "gguf":
                return self._load_gguf_model(self.model_path)
            else:
                return self._load_transformers_model(self.model_path)
            
        return self.model is not None
    
    def _load_gguf_model(self, model_path):
        """加载GGUF格式模型"""
        try:
            # 正确导入llama-cpp-python
            from llama_cpp import Llama
            
            # 设置llama.cpp的线程数
            n_threads = min(os.cpu_count() or 4, 8)
            
            # 加载GGUF模型
            self.model = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_threads=n_threads,
                verbose=False
            )
            
            print(f"成功加载GGUF模型: {model_path}")
            return True
        except ImportError as e:
            print(f"无法导入llama_cpp模块: {e}")
            print("请确保正确安装了llama-cpp-python包")
            return False
        except Exception as e:
            print(f"加载GGUF模型时出错: {e}")
            return False
    
    def _load_transformers_model(self, model_path):
        """加载Transformers模型，使用自动量化"""
        try:
            print(f"开始加载模型: {model_path}")
            
            # 使用 AutoTokenizer 加载 tokenizer
            print("加载tokenizer...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
                print("Tokenizer加载成功")
            except Exception as e:
                print(f"AutoTokenizer加载失败: {e}")
                return False
            
            # 判断模型类型，获取特定的量化配置
            model_type = "unknown"
            if "qwen" in model_path.lower():
                model_type = "qwen"
            elif "llama" in model_path.lower():
                model_type = "llama"
                
            # 获取量化配置
            quant_config = self.quantizer.get_quantization_config(model_type)
            mem_config = self.quantizer.get_memory_optimization_config()
            
            # 合并所有配置
            model_kwargs = {
                "device_map": quant_config["device_map"],
                "trust_remote_code": True,
                "torch_dtype": quant_config["torch_dtype"]
            }
            
            # 添加量化配置
            if quant_config["quantization_config"]:
                model_kwargs["quantization_config"] = quant_config["quantization_config"]
            
            # 添加内存优化配置
            for key, value in mem_config.items():
                model_kwargs[key] = value
                
            # 输出最终使用的配置
            print(f"使用模型加载配置:")
            for key, value in model_kwargs.items():
                if key != "quantization_config":  # 量化配置太复杂，不打印详情
                    print(f"  - {key}: {value}")
                else:
                    print(f"  - {key}: [已配置]")

            # 加载模型
            print("加载模型...")
            try:
                loaded_model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    **model_kwargs
                )
                
                # 检查loaded_model是否为字典，如果是则尝试提取真正的模型
                if isinstance(loaded_model, dict):
                    print("[注意] 模型加载返回了字典结构")
                    if "model" in loaded_model:
                        self.model = loaded_model["model"]
                        print(f"已从字典中提取模型: {type(self.model)}")
                    else:
                        print("[警告] 字典中未找到模型对象，使用整个字典作为模型")
                        self.model = loaded_model
                else:
                    self.model = loaded_model
                
                print("模型加载成功")
                
                # 获取实际模型对象以检查信息
                actual_model = self.model
                if isinstance(self.model, dict) and "model" in self.model:
                    actual_model = self.model["model"]
                
                # 输出模型信息
                try:
                    print(f"模型设备: {next(actual_model.parameters()).device}")
                    print(f"模型类型: {actual_model.__class__.__name__}")
                except Exception as e:
                    print(f"无法获取模型信息: {e}")
                
                # 使用的量化级别
                level_name = quant_config["level"].name
                print(f"使用的量化级别: {level_name}")
                
                # 输出显存使用情况
                if torch.cuda.is_available():
                    allocated_gb = torch.cuda.memory_allocated() / (1024**3)
                    print(f"当前显存占用: {allocated_gb:.2f} GB")
                
            except Exception as e:
                print(f"模型加载失败: {e}")
                import traceback
                traceback.print_exc()
                return False

            print(f"成功加载模型: {model_path}")
            return True
            
        except Exception as e:
            print(f"加载Transformers模型时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_response(self, response):
        """处理模型生成的响应，移除输入提示和特殊标记"""
        try:
            # 检查响应是否为空
            if not response:
                return ""
            
            print(f"[DEBUG] 原始响应长度: {len(response)} 字符")
            
            # 移除可能的输入部分和助手标识
            assistant_markers = [
                "assistant:", "Assistant:", "助手:",
                "<|assistant|>", "<assistant>",
                "<|im_start|>assistant", 
                "A:", "回答:"
            ]
            
            # 处理返回的回复
            result = response
            
            # 查找助手标记的位置
            lowest_marker_pos = len(response)
            found_marker = False
            
            for marker in assistant_markers:
                pos = response.rfind(marker)
                if pos != -1 and pos < lowest_marker_pos:
                    lowest_marker_pos = pos
                    found_marker = True
            
            # 如果找到了标记，从标记后开始截取
            if found_marker:
                for marker in assistant_markers:
                    if response[lowest_marker_pos:].startswith(marker):
                        result = response[lowest_marker_pos + len(marker):].strip()
                        break
            
            # 移除尾部可能的用户输入标记
            user_markers = [
                "user:", "User:", "用户:", 
                "<|user|>", "<user>",
                "<|im_start|>user",
                "Q:", "问题:"
            ]
            
            for marker in user_markers:
                if marker in result:
                    result = result.split(marker)[0].strip()
            
            # 去掉首尾引号
            result = result.strip('"\'')
            
            print(f"处理后的响应有 {len(result)} 个字符")
            return result
            
        except Exception as e:
            print(f"处理响应时出错: {e}")
            return response
    
    def _generate_with_gguf(self, prompt, generation_config):
        """使用GGUF模型生成文本"""
        try:
            # 设置生成参数
            params = {
                'prompt': prompt,
                'max_tokens': generation_config.get("max_new_tokens", 1024),
                'temperature': generation_config.get("temperature", 0.6),
                'top_p': generation_config.get("top_p", 0.6),
                'repeat_penalty': generation_config.get("repetition_penalty", 1.3)
            }
            
            # 生成回复
            output = self.model.generate(**params)
            
            # 从输出中提取回复
            response = output['choices'][0]['text'] if isinstance(output, dict) and 'choices' in output else output
            
            return response.strip()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"生成回复时出错: {str(e)}"
    
    def _generate_with_transformers(self, prompt, generation_config):
        """使用transformers模型生成文本"""
        try:
            # 确保模型和tokenizer已加载
            if not hasattr(self, 'model') or self.model is None:
                return "错误：模型未加载"
            if not hasattr(self, 'tokenizer') or self.tokenizer is None:
                return "错误：tokenizer未加载"
                
            # 检查模型是否是字典而不是实际模型
            if isinstance(self.model, dict):
                print("[警告] self.model是字典而不是模型对象")
                # 尝试从字典中获取模型对象
                if "model" in self.model:
                    actual_model = self.model["model"]
                    print(f"从字典中获取到模型对象: {type(actual_model)}")
                else:
                    return "错误：模型对象格式不正确，无法生成文本"
            else:
                actual_model = self.model
            
            # 将prompt转换为token
            if isinstance(prompt, str):
                # 是字符串，直接编码
                inputs = self.tokenizer(prompt, return_tensors="pt")
            else:
                # 可能是已经应用了模板的prompt，直接使用
                inputs = self.tokenizer(prompt, return_tensors="pt")
            
            print(f"输入token数量: {inputs['input_ids'].shape[1]}")
            
            # 确保输入在正确的设备上
            if hasattr(actual_model, 'device'):
                device = actual_model.device
            else:
                try:
                    device = next(actual_model.parameters()).device
                except:
                    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            print(f"使用设备: {device}")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # 设置生成参数
            gen_kwargs = {
                "max_new_tokens": generation_config.get("max_new_tokens", 1024),
                "temperature": generation_config.get("temperature", 0.4),
                "top_p": generation_config.get("top_p", 0.3),
                "top_k": generation_config.get("top_k", 15),
                "repetition_penalty": generation_config.get("repetition_penalty", 1.3),
                "do_sample": generation_config.get("do_sample", False)
            }
            
            # 执行生成
            with torch.no_grad():
                output = actual_model.generate(
                    input_ids=inputs['input_ids'], 
                    attention_mask=inputs.get('attention_mask', None),
                    **gen_kwargs
                )
            
            # 解码输出
            response_text = self.tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
            
            # 检查生成的回复是否为空
            if not response_text.strip():
                print("[警告] 模型生成了空响应")
                # 尝试直接解码整个输出
                full_text = self.tokenizer.decode(output[0], skip_special_tokens=True)
                # 尝试提取出输入提示后的部分
                original_prompt = self.tokenizer.decode(inputs['input_ids'][0], skip_special_tokens=True)
                if len(full_text) > len(original_prompt):
                    response_text = full_text[len(original_prompt):].strip()
                    print(f"[恢复] 提取到响应: {len(response_text)} 字符")
                else:
                    response_text = "模型未能生成有效回复"
                
            return response_text
            
        except Exception as e:
            import traceback
            print(f"使用transformers生成文本时出错: {e}")
            traceback.print_exc()
            return f"生成出错: {str(e)}"
            
    def generate_response(self, messages):
        """基本的响应生成方法，子类应该覆盖此方法"""
        raise NotImplementedError("子类必须实现generate_response方法")
    
    def update_settings(self, new_settings):
        """更新模型设置"""
        changed = False
        
        if new_settings.get('model_path') != self.model_path:
            self.model_path = new_settings.get('model_path')
            self.model = None
            changed = True
        
        if new_settings.get('hyperparams') != getattr(self, 'hyperparams', None):
            self.hyperparams = new_settings.get('hyperparams')
            
            # 更新温度参数
            if 'temperature' in self.hyperparams:
                self.generation_config["temperature"] = float(self.hyperparams['temperature'])
                
            changed = True
        
        if changed and self.model:
            self.load_models()
            
        return changed

    def set_model(self, model_info):
        """设置模型配置并加载模型"""
        try:
            model_path = model_info.get('path', '')
            model_name = model_info.get('name', os.path.basename(model_path))
            model_type = model_info.get('type', 'safetensors')
            
            print(f"设置模型: {model_name}, 路径: {model_path}, 类型: {model_type} ")
            
            # 保存模型路径
            self.model_path = model_path
            
            # 加载模型
            return self.load_models()
        except Exception as e:
            print(f"设置模型失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _prepare_prompt(self, messages):
        """准备基本提示信息"""
        # 使用模型的聊天模板
        if hasattr(self.tokenizer, 'apply_chat_template'):
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            # 如果没有聊天模板，使用简单拼接
            prompt = ""
            for msg in messages:
                role = "用户" if msg["role"] == "user" else "助手"
                prompt += f"{role}: {msg['content']}\n\n"
            prompt += "助手: "
        
        return prompt 
