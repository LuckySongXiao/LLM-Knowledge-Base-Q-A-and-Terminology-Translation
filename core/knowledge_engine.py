import logging
import jieba
import time
import re
from typing import List, Dict, Any, Optional, Tuple, Union
import torch

from .base_engine import BaseEngine
from .engine import Message, MessageRole
from .models import MessageResponse, GenerationConfig
from .knowledge_base import KnowledgeBase

# 配置日志
logger = logging.getLogger(__name__)

class KnowledgeEngine(BaseEngine):
    """知识库问答引擎，专门处理基于知识库的问答功能"""

    def __init__(self, model_config: Dict[str, Any], knowledge_base: Optional[KnowledgeBase] = None):
        """初始化知识库问答引擎"""
        super().__init__(model_config)

        # 导入类
        self.models = __import__('core.models', fromlist=['MessageResponse', 'GenerationConfig'])

        # 获取生成配置 - 知识库问答使用专用参数
        self.generation_config = GenerationConfig(
            max_new_tokens=model_config.get("max_new_tokens", 512),
            temperature=model_config.get("kb_temperature", model_config.get("temperature", 0.6)),  # 优先使用知识库专用温度
            top_p=model_config.get("top_p", 0.6),
            top_k=model_config.get("top_k", 15),
            repetition_penalty=model_config.get("repetition_penalty", 1.1),
        )

        # 保存知识库专用配置
        self.kb_top_k = model_config.get("kb_top_k", 15)
        self.kb_threshold = model_config.get("kb_threshold", 0.7)
        self.enable_knowledge = model_config.get("enable_knowledge", True)

        # 知识库对象
        self.knowledge_base = knowledge_base
        logger.info(f"初始化知识库问答引擎完成")

    def generate_response(self, messages, knowledge_content=None):
        """
        生成基于知识的回答

        Args:
            messages: 消息列表
            knowledge_content: 知识内容

        Returns:
            格式化的回答，包含参考内容和回答部分
        """
        try:
            # 准备提示词
            prompt = self._prepare_prompt(messages, knowledge_content)

            # 根据模型类型选择生成方法
            if self.model_type == "GGUF":
                # GGUF模型生成
                completion = self.model(prompt,
                                         max_tokens=self.max_new_tokens,
                                         temperature=self.temperature,
                                         top_p=self.top_p,
                                         top_k=self.top_k,
                                         repeat_penalty=self.repetition_penalty)
                response = completion['choices'][0]['text']
            else:
                # transformers模型生成
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.max_new_tokens,
                        do_sample=True,
                        temperature=self.temperature,
                        top_p=self.top_p,
                        top_k=self.top_k,
                        repetition_penalty=self.repetition_penalty
                    )
                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)[len(prompt):]

            # 后处理回答
            formatted_response = self._post_process_knowledge_response(response, knowledge_content)
            return formatted_response

        except Exception as e:
            logger.error(f"生成回答时出错: {str(e)}")
            return f"生成回答时出错: {str(e)}"

    def _post_process_knowledge_response(self, response, knowledge_content=None):
        """确保响应严格基于知识库内容，并包含原始知识文本。"""
        if knowledge_content is None or not knowledge_content.strip():
            return response

        # 包含原始知识文本和基于知识的回答
        formatted_response = f"""【原文信息】
{knowledge_content}

【基于原文的回答】
{response}"""

        return formatted_response

    def _check_content_overlap(self, response: str, knowledge_content: str) -> bool:
        """检查回答与知识内容是否有显著重叠

        参数:
            response: 模型回答
            knowledge_content: 知识内容

        返回:
            bool: 是否有显著重叠
        """
        # 将文本分词并提取关键词
        response_words = list(jieba.cut(response))
        knowledge_words = list(jieba.cut(knowledge_content))

        # 计算重叠度
        common_words = set(response_words) & set(knowledge_words)

        # 如果重叠词超过回答词的30%，认为有显著重叠
        if len(response_words) > 0:
            overlap_ratio = len(common_words) / len(response_words)
            return overlap_ratio > 0.3

        return False

    def _extract_relevant_knowledge(self, knowledge_items: List[Dict]) -> str:
        """提取相关知识内容

        参数:
            knowledge_items: 知识条目列表

        返回:
            str: 提取的知识内容
        """
        # 直接合并所有检索到的知识条目内容，保持原始格式和内容
        knowledge_parts = [f"条目: {item['name'] if 'name' in item else '未命名条目'}\n内容: {item['content']}"
                           for item in knowledge_items]

        # 记录提取的知识条目数量
        logger.info(f"提取了 {len(knowledge_parts)} 条知识条目")

        # 合并所有知识条目
        combined_knowledge = "\n\n".join(knowledge_parts)
        return combined_knowledge

    def _prepare_prompt(self, messages: List[Message], knowledge_content: Optional[str] = None) -> Union[str, List[Dict[str, str]]]:
        """准备模型输入提示

        Args:
            messages: 消息列表
            knowledge_content: 知识内容，可选

        Returns:
            根据模型类型返回适当格式的提示
        """
        if self.model_type == "gguf":
            if knowledge_content:
                # 确保系统消息中包含知识内容
                has_system_message = False
                for message in messages:
                    if message.role == MessageRole.SYSTEM:
                        if "知识内容:" not in message.content:
                            message.content += f"\n\n知识内容:\n{knowledge_content}"
                        has_system_message = True
                        break

                if not has_system_message:
                    # 如果没有系统消息，添加一个包含知识内容的系统消息
                    messages.insert(0, Message(
                        role=MessageRole.SYSTEM,
                        content=f"你是一个专业的问答助手。请仅根据以下提供的知识回答用户问题。如果提供的知识无法回答问题，请明确说明。\n\n知识内容:\n{knowledge_content}"
                    ))

            # 构建llama.cpp格式的提示
            prompt = ""
            for message in messages:
                if message.role == MessageRole.SYSTEM:
                    prompt += f"<|system|>\n{message.content}</s>\n"
                elif message.role == MessageRole.USER:
                    user_prefix = f"{message.name}: " if message.name else ""
                    prompt += f"<|user|>\n{user_prefix}{message.content}</s>\n"
                elif message.role == MessageRole.ASSISTANT:
                    prompt += f"<|assistant|>\n{message.content}</s>\n"

            # 添加最后的助手标记
            prompt += "<|assistant|>\n"

            return prompt

        else:  # transformers模型
            formatted_messages = []

            # 确保系统消息中包含知识内容
            has_system_message = False
            for i, message in enumerate(messages):
                msg_dict = {"role": message.role.value}

                if message.role == MessageRole.SYSTEM:
                    if knowledge_content and "知识内容:" not in message.content:
                        msg_dict["content"] = message.content + f"\n\n知识内容:\n{knowledge_content}"
                    else:
                        msg_dict["content"] = message.content
                    has_system_message = True
                else:
                    msg_dict["content"] = message.content
                    if message.name:
                        msg_dict["name"] = message.name

                formatted_messages.append(msg_dict)

            # 如果没有系统消息但有知识内容，添加一个系统消息
            if knowledge_content and not has_system_message:
                formatted_messages.insert(0, {
                    "role": MessageRole.SYSTEM.value,
                    "content": f"你是一个专业的问答助手。请仅根据以下提供的知识回答用户问题。如果提供的知识无法回答问题，请明确说明。\n\n知识内容:\n{knowledge_content}"
                })

            return formatted_messages

    def answer_question(self, question: str, top_k: int = 15) -> str:
        """
        基于知识库回答问题

        Args:
            question: 用户问题
            top_k: 返回的最相关知识项数量

        Returns:
            包含参考资料和回答的格式化响应
        """
        if not self.knowledge_base:
            return "知识库未设置，无法回答问题"

        # 获取相关知识项
        knowledge_items = self.knowledge_base.search(question, top_k)

        if not knowledge_items:
            return "未在知识库中找到相关信息"

        # 创建并格式化检索到的知识文本
        knowledge_content = self._extract_relevant_knowledge(knowledge_items)

        # 构建严格的知识库问答消息
        strict_prompt = f"""请严格按照以下知识库内容回答问题，不要添加任何额外的解释、扩展或补充说明：

知识库内容：
{knowledge_content}

用户问题：{question}

回答要求：
1. 只能基于上述知识库内容回答
2. 不得添加知识库中没有的信息
3. 不得进行推测或扩展说明
4. 如果知识库内容不足以回答问题，请直接说"知识库中没有相关的答案"
5. 回答要简洁准确，直接引用知识库内容

请回答："""

        messages = [
            Message(role=MessageRole.USER, content=strict_prompt)
        ]

        # 生成回答并返回格式化的响应（包含参考资料和回答）
        return self.generate_response(messages, knowledge_content)

    def set_knowledge_base(self, knowledge_base: KnowledgeBase) -> bool:
        """设置知识库

        参数:
            knowledge_base: 知识库对象

        返回:
            bool: 是否成功设置
        """
        self.knowledge_base = knowledge_base
        logger.info("已设置知识库")
        return True

    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """更新知识库引擎设置

        参数:
            new_settings: 新的设置字典

        返回:
            bool: 是否成功更新
        """
        try:
            # 更新知识库专用配置
            if 'kb_top_k' in new_settings:
                self.kb_top_k = new_settings['kb_top_k']
                logger.info(f"更新知识库top_k: {self.kb_top_k}")

            if 'kb_threshold' in new_settings:
                self.kb_threshold = new_settings['kb_threshold']
                logger.info(f"更新知识库阈值: {self.kb_threshold}")

            if 'enable_knowledge' in new_settings:
                self.enable_knowledge = new_settings['enable_knowledge']
                logger.info(f"更新知识库启用状态: {self.enable_knowledge}")

            # 更新生成配置
            if 'kb_temperature' in new_settings:
                if hasattr(self.generation_config, 'temperature'):
                    self.generation_config.temperature = new_settings['kb_temperature']
                elif isinstance(self.generation_config, dict):
                    self.generation_config['temperature'] = new_settings['kb_temperature']
                logger.info(f"更新知识库温度: {new_settings['kb_temperature']}")

            # 更新其他生成参数
            generation_params = ['top_p', 'top_k', 'repetition_penalty', 'max_new_tokens', 'do_sample']
            for param in generation_params:
                if param in new_settings:
                    if hasattr(self.generation_config, param):
                        setattr(self.generation_config, param, new_settings[param])
                    elif isinstance(self.generation_config, dict):
                        self.generation_config[param] = new_settings[param]
                    logger.info(f"更新知识库引擎参数 {param}: {new_settings[param]}")

            # 调用父类的更新方法
            if hasattr(super(), 'update_settings'):
                super().update_settings(new_settings)

            logger.info("知识库引擎设置更新完成")
            return True

        except Exception as e:
            logger.error(f"更新知识库引擎设置失败: {e}")
            return False