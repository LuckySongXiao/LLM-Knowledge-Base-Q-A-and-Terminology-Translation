import logging
import torch
from .base_engine import BaseEngine

# 配置日志
logger = logging.getLogger(__name__)

class ChatEngine(BaseEngine):
    """聊天引擎，处理普通对话功能"""
    
    def __init__(self, settings):
        """初始化聊天引擎"""
        super().__init__(settings)
        
        # 聊天引擎特定的生成配置
        self.generation_config = {
            "max_new_tokens": 1024,  # 最大生成长度
            "temperature": 0.7,      # 温度参数：聊天使用较高温度鼓励创造性
            "top_p": 0.9,            # top-p采样：提高多样性
            "top_k": 40,             # top-k采样：更多选择
            "repetition_penalty": 1.1,  # 重复惩罚：轻微惩罚重复
            "do_sample": True        # 使用采样：启用采样提高回复多样性
        }
        
        # 从设置中读取温度参数
        temperature = float(settings.get('temperature', 0.7))
        self.generation_config["temperature"] = temperature
        
        logger.info(f"初始化聊天引擎完成，温度参数: {temperature}")
        self.persona = settings.get('persona', '')
    
    def generate_response(self, messages):
        """根据提供的消息生成聊天回复"""
        try:
            if not messages:
                return "错误：未提供消息"
            
            # 获取并记录模型类型和设备
            if hasattr(self, 'model') and self.model:
                if isinstance(self.model, dict):
                    # 处理自定义模型字典格式
                    self.model_type = self.model.get('type', '未知类型')
                    if 'device' in self.model:
                        self.device = self.model['device']
                    elif 'model' in self.model and hasattr(self.model['model'], 'device'):
                        self.device = self.model['model'].device
                    else:
                        self.device = "cuda" if torch.cuda.is_available() else "cpu"
                else:
                    # 处理标准模型对象
                    self.model_type = self.model.__class__.__name__
                    if hasattr(self.model, 'device'):
                        self.device = self.model.device
                    elif hasattr(self.model, 'parameters'):
                        try:
                            self.device = next(self.model.parameters()).device
                        except:
                            self.device = "cpu"
                    else:
                        self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.model_type = "未加载模型"
                self.device = "未知设备"
            
            # 记录提交给模型的消息
            logger.info(f"使用模型: {self.model_type}，设备: {self.device}")
            
            # 如果模型是字典格式且包含model键，使用custom_generate
            if isinstance(self.model, dict) and 'model' in self.model and 'tokenizer' in self.model:
                return self._custom_generate(messages)
            
            # 普通生成回应方法
            if self.model and self.tokenizer:
                # 尝试将模型移至GPU(如果可用且模型不在GPU上)
                if str(self.device) == 'cpu' and torch.cuda.is_available():
                    try:
                        logger.info("尝试将模型移动到GPU...")
                        if isinstance(self.model, dict) and 'model' in self.model:
                            self.model['model'] = self.model['model'].to('cuda')
                            self.device = 'cuda'
                        else:
                            self.model = self.model.to('cuda')
                            self.device = 'cuda'
                        logger.info(f"模型已成功移至GPU: {self.device}")
                    except Exception as e:
                        logger.warning(f"将模型移至GPU失败: {e}")
                
                # 格式化消息
                # 根据模型类型处理生成
                if hasattr(self, 'gguf_model') and self.gguf_model:
                    # 准备GGUF模型的输入
                    prompt = self._prepare_prompt(messages)
                    
                    # 使用GGUF模型生成回复
                    response = self._generate_with_gguf(prompt, self.generation_config)
                    return self._clean_response(response)
                    
                elif hasattr(self, 'model') and self.model:
                    # 使用transformers模型生成回复
                    if hasattr(self.tokenizer, 'apply_chat_template') and callable(getattr(self.tokenizer, 'apply_chat_template')):
                        # 使用Qwen2.5聊天模板格式化输入
                        try:
                            # 确保系统消息存在
                            if not any(msg.get("role") == "system" for msg in messages):
                                messages.insert(0, {
                                    "role": "system", 
                                    "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
                                })
                                
                            text = self.tokenizer.apply_chat_template(
                                messages,
                                tokenize=False,
                                add_generation_prompt=True
                            )
                            logger.info(f"使用Qwen2.5聊天模板格式化输入，长度: {len(text)}")
                            
                            # 转换为模型输入
                            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
                            
                            # 生成回复
                            generated_ids = self.model.generate(
                                **model_inputs,
                                max_new_tokens=self.generation_config.get("max_new_tokens", 512),
                                temperature=self.generation_config.get("temperature", 0.7),
                                top_p=self.generation_config.get("top_p", 0.9),
                                top_k=self.generation_config.get("top_k", 40),
                                repetition_penalty=self.generation_config.get("repetition_penalty", 1.1),
                                do_sample=self.generation_config.get("do_sample", True)
                            )
                            
                            # 提取生成的部分
                            generated_ids = [
                                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                            ]
                            
                            # 解码生成的回复
                            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
                            
                            return response
                            
                        except Exception as e:
                            logger.warning(f"使用Qwen2.5格式生成失败: {e}，尝试使用传统方式")
                            conversation = self._prepare_prompt(messages)
                            response = self._generate_with_transformers(conversation, self.generation_config)
                            return self._process_response(response)
                    else:
                        # 手动构建提示
                        conversation = self._prepare_prompt(messages)
                        
                        logger.info("开始生成聊天回复...")
                        
                        # 使用transformers生成回复
                        response = self._generate_with_transformers(conversation, self.generation_config)
                        
                        # 处理输出，移除输入提示
                        return self._process_response(response)
                    
                else:
                    return "错误：模型未加载"
            
        except Exception as e:
            import traceback
            logger.error(f"生成聊天回复时出错: {e}")
            traceback.print_exc()
            return f"生成聊天回复时出错: {str(e)}"
    
    def _prepare_prompt(self, messages):
        """准备聊天提示信息"""
        # 如果有人设，插入到系统消息中
        if self.persona and messages:
            has_system = False
            for message in messages:
                if message["role"] == "system":
                    has_system = True
                    # 如果现有的系统消息中没有人设信息，添加人设
                    if self.persona not in message["content"]:
                        message["content"] = self.persona + "\n\n" + message["content"]
                    break
            
            # 如果没有系统消息，添加一个
            if not has_system:
                messages.insert(0, {"role": "system", "content": self.persona})
                
        return super()._prepare_prompt(messages)
    
    def _clean_response(self, response):
        """清理和处理模型生成的响应文本"""
        if not response:
            return ""
        
        # 移除可能的系统提示和用户输入重复
        response = self._process_response(response)
        
        # 确保响应不为空
        if not response.strip():
            return response.strip()
        
        # 移除多余的空行和空格
        response = "\n".join(line.strip() for line in response.split("\n") if line.strip())
        
        return response
        
    def set_persona(self, persona):
        """设置聊天人设"""
        self.persona = persona
        logger.info(f"已设置聊天人设: {persona[:50]}...")
        return True
        
    def update_settings(self, new_settings):
        """更新聊天引擎设置"""
        changed = super().update_settings(new_settings)
        
        # 检查是否有人设更新
        if new_settings.get('persona') != self.persona:
            self.persona = new_settings.get('persona', '')
            changed = True
            
        return changed 

    def _custom_generate(self, messages):
        """使用自定义模型字典格式生成回复"""
        try:
            # 提取模型和tokenizer
            model = self.model.get('model')
            tokenizer = self.model.get('tokenizer')
            
            if not model or not tokenizer:
                return "错误: 模型或tokenizer未正确加载"
            
            # 确保模型在GPU上(如果可用)
            device = model.device if hasattr(model, 'device') else 'cpu'
            if 'cuda' not in str(device) and torch.cuda.is_available():
                logger.info(f"模型当前在{device}上，尝试移至GPU...")
                try:
                    model = model.to('cuda')
                    logger.info(f"模型已成功移至GPU: {model.device}")
                except Exception as e:
                    logger.warning(f"将模型移至GPU失败: {e}")
            
            # 使用apply_chat_template格式化对话
            try:
                text = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            except Exception as e:
                logger.warning(f"使用chat_template格式化失败: {e}，尝试手动格式化")
                # 手动格式化输入
                text = self._format_chat_manually(messages)
            
            # 转换为模型输入
            model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
            
            # 获取生成参数
            gen_kwargs = {
                "max_new_tokens": self.generation_config.get("max_new_tokens", 512),
                "temperature": self.generation_config.get("temperature", 0.7),
                "top_p": self.generation_config.get("top_p", 0.9),
                "top_k": self.generation_config.get("top_k", 50),
                "repetition_penalty": self.generation_config.get("repetition_penalty", 1.2),
                "do_sample": self.generation_config.get("do_sample", True)
            }
            
            # 生成回复
            generated_ids = model.generate(
                **model_inputs,
                **gen_kwargs
            )
            
            # 提取生成的部分
            try:
                generated_ids = [
                    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                ]
                
                # 解码生成的回复
                response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
                return response
            except Exception as e:
                logger.error(f"解码生成回复失败: {e}")
                # 直接解码整个输出
                return tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        
        except Exception as e:
            logger.error(f"自定义生成过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return f"生成回复时出现错误: {str(e)}"
    
    def _format_chat_manually(self, messages):
        """手动格式化聊天消息"""
        formatted_text = ""
        
        for msg in messages:
            role = msg.get('role', '').lower()
            content = msg.get('content', '')
            
            if role == 'system':
                formatted_text += f"<system>\n{content}\n</system>\n\n"
            elif role == 'user':
                formatted_text += f"<human>\n{content}\n</human>\n\n"
            elif role == 'assistant':
                formatted_text += f"<assistant>\n{content}\n</assistant>\n\n"
        
        # 添加最终的assistant标签，提示模型回复
        formatted_text += "<assistant>\n"
        
        return formatted_text 