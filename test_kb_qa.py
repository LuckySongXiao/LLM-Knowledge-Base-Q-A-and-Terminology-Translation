#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库问答测试脚本
"""

import os
import sys
import logging
import json
import time
from typing import Dict, Any, List, Optional

# 配置日志输出格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_kb_qa')

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from core.engine import Message, MessageRole
from core.models import MessageResponse
from core.knowledge_engine import KnowledgeEngine
from core.knowledge_base import KnowledgeBase

# 模拟知识库类
class MockKnowledgeBase:
    def __init__(self):
        self.items = {}
    
    def add_item(self, name, content, metadata=None):
        self.items[name] = {
            'content': content,
            'metadata': metadata or {}
        }
        return True
    
    def search(self, query, top_k=15, threshold=0.0):
        """简单的模拟搜索，返回所有知识条目"""
        results = []
        
        for name, item in self.items.items():
            # 简单计算相似度：检查查询词是否在内容中
            similarity = 0.5  # 默认相似度
            if query.lower() in item['content'].lower():
                similarity = 0.8  # 如果查询词直接出现，给更高分数
            
            results.append((
                MockKnowledgeItem(name, item['content'], item['metadata']), 
                similarity
            ))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class MockKnowledgeItem:
    def __init__(self, name, content, metadata=None):
        self.name = name
        self.content = content
        self.metadata = metadata or {}
    
    def to_dict(self):
        return {
            'name': self.name,
            'content': self.content,
            'metadata': self.metadata
        }


def test_knowledge_qa():
    """测试知识库问答功能"""
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
    
    # 创建知识库引擎，使用最小配置
    engine_config = {
        "max_new_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    
    # 模拟KnowledgeEngine的行为
    class MockKnowledgeEngine:
        def __init__(self, config, knowledge_base):
            self.config = config
            self.knowledge_base = knowledge_base
        
        def _post_process_knowledge_response(self, response, knowledge_content):
            """确保响应基于知识库中的内容"""
            return f"""【原文信息】
{knowledge_content}

【基于原文的回答】
{response}"""
        
        def generate_response(self, messages, knowledge_content=None):
            """简单的响应生成"""
            query = messages[-1]["content"] if isinstance(messages, list) and messages else ""
            
            if "Python" in query:
                response = "Python是一种高级编程语言，由吉多·范罗苏姆创建于1991年。它以简洁的语法和丰富的库生态系统著称。"
            elif "人工智能" in query:
                response = "人工智能是计算机科学的一个分支，致力于创造能够执行通常需要人类智能的任务的系统。它包括机器学习、深度学习等子领域。"
            elif "量子计算" in query:
                response = "量子计算是利用量子力学现象进行计算的技术，使用量子位代替传统的位作为信息单元，在某些任务上能比传统计算机快得多。"
            else:
                response = "我无法回答这个问题。"
            
            # 处理知识库响应
            if knowledge_content:
                return self._post_process_knowledge_response(response, knowledge_content)
            return response
        
        def answer_question(self, query, top_k=15):
            """基于知识库回答问题"""
            # 获取相关知识
            search_results = self.knowledge_base.search(query, top_k=top_k)
            
            if not search_results:
                return "在知识库中未找到相关信息"
            
            # 构建知识内容
            knowledge_content = ""
            for i, (item, score) in enumerate(search_results):
                knowledge_content += f"知识 {i+1}:\n{item.content}\n\n"
            
            # 创建消息
            messages = [{"role": "user", "content": query}]
            
            # 生成回答
            response = self.generate_response(messages, knowledge_content)
            
            return response
    
    # 创建引擎
    engine = MockKnowledgeEngine(engine_config, kb)
    
    # 测试问题
    test_questions = [
        "Python是什么时候创建的？",
        "什么是人工智能？它有哪些应用？",
        "量子计算机与传统计算机有什么区别？",
        "区块链是什么技术？"  # 测试知识库中没有的内容
    ]
    
    # 执行测试
    print("\n===== 知识库问答测试 =====\n")
    for question in test_questions:
        print(f"问题: {question}")
        start_time = time.time()
        answer = engine.answer_question(question)
        end_time = time.time()
        
        print(f"回答:\n{answer}")
        print(f"耗时: {end_time - start_time:.2f}秒")
        print("-" * 50)


def test_updated_knowledge_qa():
    """测试改进后的知识库问答功能，确保回答中包含原始知识文本和基于知识的回答。"""
    print("初始化知识库和知识引擎...")
    
    # 创建临时知识库目录
    os.makedirs("temp/kb_test", exist_ok=True)
    
    # 初始化知识库
    kb = KnowledgeBase(
        vector_db_path="temp/kb_test/test_vector_db",
        embedding_device="cpu"
    )
    
    # 添加测试知识条目
    test_items = [
        {
            "name": "python基础知识",
            "content": "Python是一种高级编程语言，以其简洁易读的语法著称。Python支持多种编程范式，包括面向对象、命令式和函数式编程。Python的设计强调代码的可读性，它的语法允许开发者用更少的代码行数表达概念。"
        },
        {
            "name": "人工智能简介",
            "content": "人工智能(AI)是计算机科学的一个分支，旨在创建能够模拟人类智能行为的系统。AI可以分为两大类：弱AI（专注于执行特定任务）和强AI（能够执行任何智力任务）。目前的AI技术主要集中在机器学习、深度学习和自然语言处理等领域。"
        },
        {
            "name": "量子计算基础",
            "content": "量子计算是一种利用量子力学现象（如叠加和纠缠）进行计算的技术。与传统计算机使用位（0或1）不同，量子计算机使用量子比特（可以同时是0和1的状态）。这使得量子计算机在某些特定问题上比传统计算机更高效。"
        }
    ]
    
    for item in test_items:
        print(f"添加知识条目: {item['name']}")
        kb.add_item(item["name"], item["content"])
    
    # 初始化知识引擎
    engine = KnowledgeEngine()
    engine.set_knowledge_base(kb)
    
    # 测试问题
    test_questions = [
        "Python有哪些编程范式？",
        "什么是人工智能，它有哪些分类？",
        "量子计算和传统计算有什么区别？"
    ]
    
    # 测试知识库问答
    for question in test_questions:
        print("\n" + "="*50)
        print(f"问题: {question}")
        
        start_time = time.time()
        
        # 创建消息
        messages = [Message(role=MessageRole.USER, content=question)]
        
        # 调用知识库引擎回答问题
        response = engine.answer_question(messages)
        
        end_time = time.time()
        
        print(f"响应: \n{response}")
        print(f"查询时间: {end_time - start_time:.2f}秒")
    
    print("\n测试完成!")


if __name__ == "__main__":
    test_updated_knowledge_qa() 