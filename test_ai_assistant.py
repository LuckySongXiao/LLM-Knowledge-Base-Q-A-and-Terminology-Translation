#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
松瓷机电AI助手测试脚本 - 专注于知识库问答
"""

import os
import sys
import logging
import json
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_assistant')

# 添加当前目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 知识库测试类
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

# 知识库问答引擎
class KnowledgeQAEngine:
    def __init__(self):
        self.knowledge_base = MockKnowledgeBase()
        
        # 添加示例知识
        self._add_sample_knowledge()
    
    def _add_sample_knowledge(self):
        """添加示例知识到知识库"""
        self.knowledge_base.add_item(
            "Python编程语言", 
            "Python是一种高级编程语言，由吉多·范罗苏姆于1991年创建。它以简洁、易读的语法和强大的库生态系统而闻名。Python支持多种编程范式，包括面向对象、命令式和函数式编程。它拥有动态类型系统和自动内存管理。Python被广泛应用于web开发、数据分析、人工智能、科学计算和自动化等领域。"
        )
        
        self.knowledge_base.add_item(
            "人工智能基础",
            "人工智能(AI)是计算机科学的一个分支，致力于创造能够模拟人类智能的系统。AI包括机器学习、深度学习、自然语言处理和计算机视觉等多个子领域。机器学习使计算机能够从数据中学习并做出预测，而无需明确编程。深度学习是机器学习的一个子集，使用多层神经网络进行特征提取和模式识别。AI在医疗诊断、自动驾驶、智能助手和游戏等领域有广泛应用。"
        )
        
        self.knowledge_base.add_item(
            "量子计算简介",
            "量子计算是一种利用量子力学现象（如叠加和纠缠）进行计算的技术。传统计算机使用位(0或1)作为信息的基本单元，而量子计算机使用量子位(qubit)，可以同时表示0和1的叠加态。这使得量子计算机在某些计算任务上比经典计算机快得多。量子计算的主要挑战包括量子退相干和错误校正。IBM、Google和微软等公司正在研发实用的量子计算机。"
        )
    
    def generate_answer(self, query):
        """生成基于知识库的回答"""
        start_time = time.time()
        
        # 1. 从知识库获取相关知识
        search_results = self.knowledge_base.search(query, top_k=15)
        
        if not search_results:
            return "在知识库中未找到相关信息"
        
        # 2. 将搜索结果拼接成知识内容
        knowledge_content = ""
        for i, (item, score) in enumerate(search_results):
            knowledge_content += f"知识 {i+1}:\n{item.content}\n\n"
        
        # 3. 简单模拟大模型生成回答
        if "Python" in query:
            response = "Python是一种高级编程语言，由吉多·范罗苏姆创建于1991年。它以简洁的语法和丰富的库生态系统著称。"
        elif "人工智能" in query:
            response = "人工智能是计算机科学的一个分支，致力于创造能够执行通常需要人类智能的任务的系统。它包括机器学习、深度学习等子领域。"
        elif "量子计算" in query:
            response = "量子计算是利用量子力学现象进行计算的技术，使用量子位代替传统的位作为信息单元，在某些任务上能比传统计算机快得多。"
        else:
            response = "我无法回答这个问题。"
        
        # 4. 格式化回答，确保包含原文信息
        formatted_response = f"""【原文信息】
{knowledge_content}

【基于原文的回答】
{response}"""
        
        end_time = time.time()
        
        return formatted_response

def test_knowledge_qa():
    """测试知识库问答功能"""
    # 创建引擎
    engine = KnowledgeQAEngine()
    
    # 测试问题
    questions = [
        "Python是什么时候创建的？",
        "什么是人工智能？它有哪些应用？",
        "量子计算机与传统计算机有什么区别？"
    ]
    
    # 执行测试
    print("\n===== 知识库问答测试 =====\n")
    for question in questions:
        print(f"问题: {question}")
        
        start_time = time.time()
        answer = engine.generate_answer(question)
        end_time = time.time()
        
        print(f"回答:\n{answer}")
        print(f"耗时: {end_time - start_time:.2f}秒")
        print("-" * 80)
        print()

if __name__ == "__main__":
    test_knowledge_qa() 