#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库问答引擎测试脚本
"""

import os
import sys
import logging
import json
import re
import jieba
import time
from typing import List, Dict, Any, Optional
from core.engine import Message, MessageRole
from core.knowledge_engine import KnowledgeEngine
from core.knowledge_base import KnowledgeBase
from core.vector_db import VectorDB

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_knowledge_engine')

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # 获取父目录
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)  # 将父目录添加到路径中

# 现在尝试导入
try:
    from core.knowledge_engine import KnowledgeEngine
    from core.message import Message, MessageRole, MessageResponse
    print("成功导入core.message模块")
except ImportError as e:
    print(f"导入错误: {e}")
    # 创建模拟类用于测试
    class Message:
        def __init__(self, role, content):
            self.role = role
            self.content = content
    
    class MessageRole:
        SYSTEM = "system"
        USER = "user"
        ASSISTANT = "assistant"
    
    class MessageResponse:
        def __init__(self, content, generation_time=0, metadata=None):
            self.content = content
            self.generation_time = generation_time
            self.metadata = metadata or {}

# 创建模拟知识库和知识条目类
class MockKnowledgeItem:
    def __init__(self, name, content, metadata=None):
        self.name = name
        self.content = content
        self.metadata = metadata or {}
    
    def to_dict(self):
        return {
            "name": self.name,
            "content": self.content,
            "metadata": self.metadata
        }

class MockKnowledgeBase:
    def __init__(self):
        self.items = {}
    
    def add_item(self, name, content, metadata=None):
        self.items[name] = MockKnowledgeItem(name, content, metadata)
        return True
    
    def search(self, query, top_k=15):
        # 简单的模拟搜索，返回所有知识条目
        results = []
        for name, item in self.items.items():
            # 简单的相关性评分 (0-1)
            similarity = 0.0
            
            # 检查查询词是否在内容中
            if query.lower() in item.content.lower():
                similarity = 0.8  # 如果查询词在内容中直接出现，给予较高分数
            else:
                # 基于词汇重叠的简单相似度计算
                query_words = set(jieba.cut(query))
                content_words = set(jieba.cut(item.content))
                common_words = query_words.intersection(content_words)
                
                if common_words:
                    similarity = len(common_words) / len(query_words) * 0.7
            
            # 如果相似度大于0，添加到结果中
            if similarity > 0:
                results.append((item, similarity))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

# 模拟引擎类
class MockEngine:
    def __init__(self, model_type="gguf"):
        self.model_type = model_type
        self.knowledge_base = None
    
    def _prepare_prompt(self, messages, knowledge_content=None):
        """根据消息和知识库内容准备提示"""
        if knowledge_content:
            prompt = f"""请严格基于以下的背景知识回答问题，不要编造不存在于背景中的内容，如果背景知识不足以回答问题，请直接回答"对不起，我没有足够的信息来回答这个问题"。

背景知识：
{knowledge_content}

请注意：你的回答必须严格遵循以下格式，缺一不可：
【原文信息】
（在这里必须逐字引用与问题直接相关的背景知识原文，不要改写或总结。如果有多个相关段落，请全部引用）
【基于原文的回答】
（在这里提供完全基于原文信息的回答，不要添加背景知识中不存在的信息）

用户问题：{messages[-1].content}"""
            return prompt
        else:
            return messages[-1].content
    
    def _post_process_knowledge_response(self, response, knowledge_content):
        """确保响应基于知识库中的内容"""
        if not response.strip():
            return "对不起，我无法根据提供的信息生成回答。"
            
        # 检查是否已经包含了格式化的回答
        if "【原文信息】" in response and "【基于原文的回答】" in response:
            return response
            
        # 从知识内容中提取最相关的部分
        relevant_content = self._extract_relevant_knowledge(response, knowledge_content)
        
        # 添加格式化的回答
        if not relevant_content:
            # 使用整个知识内容作为原文信息
            formatted_response = f"【原文信息】\n{knowledge_content}\n\n【基于原文的回答】\n{response}"
        else:
            formatted_response = f"【原文信息】\n{relevant_content}\n\n【基于原文的回答】\n{response}"
            
        return formatted_response
    
    def _extract_relevant_knowledge(self, response, knowledge_content):
        """从知识内容中提取与回答相关的部分"""
        # 首先尝试从知识内容中提取已编号的知识条目
        knowledge_entries = re.findall(r'知识 \d+:\n(.*?)(?=知识 \d+:|\Z)', knowledge_content, re.DOTALL)
        
        if not knowledge_entries:
            # 如果没有找到知识条目格式，按句子分割
            sentences = re.split(r'(?<=[。！？.!?])\s*', knowledge_content)
            
            # 分词并创建回答中的关键词集合
            response_words = set(jieba.lcut(response.lower()))
            important_words = [w for w in response_words if len(w) > 1]  # 只保留长度大于1的词
            
            # 为每个句子计算得分
            sentence_scores = []
            for sentence in sentences:
                if len(sentence.strip()) < 5:  # 忽略太短的句子
                    continue
                    
                # 分词并计算与回答的词汇重叠度
                sentence_words = set(jieba.lcut(sentence.lower()))
                overlap = sentence_words.intersection(response_words)
                
                # 计算重要词汇的重叠度
                important_overlap = [w for w in important_words if w in sentence.lower()]
                
                # 如果有足够的重叠，认为这个句子是相关的
                if len(overlap) >= min(3, len(sentence_words) / 4) or len(important_overlap) >= 2:
                    # 计算相关性得分
                    score = (len(overlap) / len(sentence_words)) + (len(important_overlap) * 0.5)
                    sentence_scores.append((sentence, score))
            
            # 按得分排序句子
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 选择得分最高的前几个句子
            if sentence_scores:
                # 取得分最高的前5个句子
                top_sentences = [s[0] for s in sentence_scores[:5]]
                
                # 恢复原始顺序（按在文档中的位置排序）
                ordered_sentences = [s for s in sentences if s in top_sentences]
                
                return ' '.join(ordered_sentences)
            else:
                # 如果找不到明确相关的部分，返回前几句作为上下文
                return ' '.join(sentences[:min(5, len(sentences))])
        else:
            # 如果找到了知识条目，检查每个条目与回答的相关性
            response_words = set(jieba.lcut(response.lower()))
            important_words = [w for w in response_words if len(w) > 1]
            
            entry_scores = []
            for entry in knowledge_entries:
                entry_words = set(jieba.lcut(entry.lower()))
                overlap = entry_words.intersection(response_words)
                important_overlap = [w for w in important_words if w in entry.lower()]
                
                if len(overlap) > 0 or len(important_overlap) > 0:
                    score = (len(overlap) / len(entry_words) if entry_words else 0) + (len(important_overlap) * 0.5)
                    entry_scores.append((entry, score))
            
            # 按得分排序知识条目
            entry_scores.sort(key=lambda x: x[1], reverse=True)
            
            if entry_scores:
                # 返回最相关的知识条目 (最多3个)
                return '\n\n'.join([e[0] for e in entry_scores[:3]])
            else:
                # 如果没有明确相关的条目，返回所有条目作为上下文
                return '\n\n'.join(knowledge_entries)
    
    def generate_response(self, prompt):
        """模拟生成回答的过程"""
        # 简单的回答生成逻辑，实际应该由LLM完成
        if "Python" in prompt:
            return "Python是一种广泛使用的解释型、高级编程语言，其设计强调代码的可读性和简洁的语法。"
        elif "人工智能" in prompt:
            return "人工智能是计算机科学的一个分支，致力于创造能够执行通常需要人类智能的任务的系统。"
        elif "量子计算" in prompt:
            return "量子计算是一种利用量子力学现象（如叠加和纠缠）进行计算的计算模型。"
        else:
            return "我没有找到与您问题相关的信息。"
    
    def answer_question(self, query):
        """从知识库回答问题"""
        start_time = time.time()
        
        # 从知识库中获取最相关的项目
        try:
            results = self.knowledge_base.search(query, top_k=15)
            if not results:
                return MessageResponse(
                    content="我在知识库中没有找到与您问题相关的信息。",
                    generation_time=time.time() - start_time
                )
        except Exception as e:
            logger.error(f"知识库搜索错误: {e}")
            return MessageResponse(
                content=f"知识库搜索时发生错误: {str(e)}",
                generation_time=time.time() - start_time
            )
        
        # 构建知识内容
        knowledge_items = []
        knowledge_content = ""
        raw_knowledge = []
        
        for i, (item, score) in enumerate(results, 1):
            knowledge_items.append(item)
            knowledge_content += f"知识 {i}:\n{item.content}\n\n"
            raw_knowledge.append({
                "title": item.name,
                "content": item.content,
                "similarity_score": float(score)
            })
        
        # 构建消息列表
        messages = [
            Message(role=MessageRole.SYSTEM, content="你是一个严格的知识库助手，你的回答必须完全基于提供的知识内容。"),
            Message(role=MessageRole.USER, content=query)
        ]
        
        # 生成最终提示词
        prompt = self._prepare_prompt(messages, knowledge_content)
        
        # 模拟生成回答
        raw_response = self.generate_response(prompt)
        
        # 处理回答，确保严格基于知识内容
        response_content = self._post_process_knowledge_response(raw_response, knowledge_content)
        
        end_time = time.time()
        
        # 构建完整的响应
        return MessageResponse(
            content=response_content,
            generation_time=end_time - start_time,
            metadata={
                "knowledge_items": [item.to_dict() for item in knowledge_items],
                "raw_retrieved_knowledge": raw_knowledge
            }
        )
    
    def set_knowledge_base(self, knowledge_base):
        """设置知识库"""
        self.knowledge_base = knowledge_base
        logger.info("已设置知识库")
        return True

def test_knowledge_engine():
    """测试知识库问答引擎"""
    # 创建模拟知识库
    kb = MockKnowledgeBase()
    
    # 添加测试知识条目
    kb.add_item(
        "Python编程语言", 
        "Python是一种高级编程语言，由吉多·范罗苏姆于1991年创建。它以简洁、易读的语法和强大的库生态系统而闻名。Python支持多种编程范式，包括面向对象、命令式和函数式编程。它拥有动态类型系统和自动内存管理。Python被广泛应用于web开发、数据分析、人工智能、科学计算和自动化等领域。"
    )
    
    kb.add_item(
        "人工智能基础",
        "人工智能(AI)是计算机科学的一个分支，致力于创造能够模拟人类智能的系统。AI包括机器学习、深度学习、自然语言处理和计算机视觉等多个子领域。机器学习使计算机能够从数据中学习并做出预测，而无需明确编程。深度学习是机器学习的一个子集，使用多层神经网络进行特征提取和模式识别。AI在医疗诊断、自动驾驶、智能助手和游戏等领域有广泛应用。"
    )
    
    kb.add_item(
        "量子计算简介",
        "量子计算是一种利用量子力学现象（如叠加和纠缠）进行计算的技术。传统计算机使用位(0或1)作为信息的基本单元，而量子计算机使用量子位(qubit)，可以同时表示0和1的叠加态。这使得量子计算机在某些计算任务上比经典计算机快得多。量子计算的主要挑战包括量子退相干和错误校正。IBM、Google和微软等公司正在研发实用的量子计算机。"
    )
    
    kb.add_item(
        "自然语言处理技术",
        "自然语言处理(NLP)是人工智能的一个分支，专注于计算机理解、解释和生成人类语言。NLP技术包括文本分类、情感分析、命名实体识别、机器翻译和问答系统等。现代NLP系统大多基于深度学习模型，如循环神经网络(RNN)、长短期记忆网络(LSTM)和Transformer架构。BERT、GPT和T5等预训练语言模型在各种NLP任务上取得了突破性进展。NLP应用广泛，包括聊天机器人、语音助手、搜索引擎和内容生成等。"
    )
    
    kb.add_item(
        "机器学习基础知识",
        "机器学习是人工智能的核心技术，它使计算机系统能够从数据中学习并改进，而无需明确编程。机器学习主要分为三类：监督学习、无监督学习和强化学习。监督学习使用标记数据训练模型，包括分类和回归任务。无监督学习处理未标记数据，用于聚类和降维。强化学习通过奖励和惩罚机制使系统学习最佳行为。常见的机器学习算法包括线性回归、决策树、随机森林、支持向量机和神经网络等。特征工程、模型评估和处理过拟合是机器学习中的关键挑战。"
    )
    
    # 创建模拟引擎并设置知识库
    engine = MockEngine()
    engine.set_knowledge_base(kb)
    
    # 测试不同问题
    test_questions = [
        "Python是什么时候创建的？它有哪些特点？",
        "什么是自然语言处理？它有哪些应用？",
        "机器学习和深度学习有什么区别？",
        "量子计算机与传统计算机相比有什么优势？",
        "人工智能目前在医疗领域有哪些应用？"
    ]
    
    # 测试知识引擎回答
    print("======== 开始测试知识库问答引擎 ========")
    for question in test_questions:
        print(f"\n问题: {question}")
        response = engine.answer_question(question)
        print(f"\n回答:\n{response.content}")
        
        # 验证回答格式是否正确
        if "【原文信息】" in response.content and "【基于原文的回答】" in response.content:
            print("\n✓ 回答格式正确")
        else:
            print("\n✗ 回答格式错误 - 缺少原文信息或基于原文的回答部分")
            
        # 检查元数据
        if response.metadata and "raw_retrieved_knowledge" in response.metadata:
            print(f"检索到 {len(response.metadata['raw_retrieved_knowledge'])} 条相关知识")
            
        print("------------------------------------")
    
    print("\n======== 测试完成 ========")

def main():
    """测试知识库引擎的响应格式，确保输出包含原始知识内容"""
    print("开始测试知识库引擎...")
    
    # 模拟配置
    model_config = {
        "max_new_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 15,
        "repetition_penalty": 1.1,
    }
    
    # 模拟向量数据库
    print("初始化向量数据库...")
    vector_db = VectorDB({
        "vector_db_path": "./data/vector_db",
        "vector_model_path": "./BAAI/bge-m3"
    })
    vector_db.initialize()
    
    # 初始化知识库
    print("初始化知识库...")
    knowledge_base = KnowledgeBase(vector_db, {})
    
    # 初始化知识引擎
    print("初始化知识引擎...")
    knowledge_engine = KnowledgeEngine(model_config, knowledge_base)
    
    # 添加测试知识条目
    test_knowledge = "人工智能（Artificial Intelligence，AI）是一门研究如何使计算机模拟人类智能的科学。" \
                     "它包括机器学习、深度学习、自然语言处理等子领域。" \
                     "自1956年达特茅斯会议以来，AI经历了多次发展浪潮，目前正处于蓬勃发展时期。"
    
    # 测试响应格式
    messages = [
        Message(role=MessageRole.SYSTEM, content="你是一个知识库助手，请基于提供的知识回答问题。"),
        Message(role=MessageRole.USER, content="什么是人工智能？")
    ]
    
    # 生成响应
    print("测试响应格式...")
    response = knowledge_engine._post_process_knowledge_response("人工智能是一门研究计算机如何模拟人类智能的科学，包括机器学习等领域。", test_knowledge)
    
    print("\n===== 响应内容 =====")
    print(response)
    print("====================\n")
    
    # 验证响应是否包含原始知识内容
    if "【原文信息】" in response and "【基于原文的回答】" in response:
        print("测试通过：响应包含原始知识内容和基于原文的回答")
    else:
        print("测试失败：响应格式不符合预期")
    
    # 尝试实际生成回答（如果模型已加载）
    try:
        if hasattr(knowledge_engine, 'model') and knowledge_engine.model:
            print("尝试使用模型生成回答...")
            full_response = knowledge_engine.generate_response(messages, test_knowledge)
            print("\n===== 模型生成的完整响应 =====")
            print(full_response)
            print("==============================\n")
    except Exception as e:
        print(f"模型生成回答时出错: {e}")

# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    main() 
