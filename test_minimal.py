#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最小化知识库问答测试
"""

def format_knowledge_response(response, knowledge_content):
    """格式化知识库回答，确保包含原文和回答"""
    if not response.strip():
        return "无法回答该问题"
    
    if "【原文信息】" in response and "【基于原文的回答】" in response:
        return response
    
    formatted_response = f"""【原文信息】
{knowledge_content}

【基于原文的回答】
{response}"""
    
    return formatted_response


def test_format():
    """测试格式化功能"""
    # 测试知识
    knowledge = """Python是一种高级编程语言，由吉多·范罗苏姆于1991年创建。它以简洁、易读的语法和强大的库生态系统而闻名。
Python支持多种编程范式，包括面向对象、命令式和函数式编程。它拥有动态类型系统和自动内存管理。
Python被广泛应用于web开发、数据分析、人工智能、科学计算和自动化等领域。"""
    
    # 测试回答
    response = "Python是一种高级编程语言，由吉多·范罗苏姆创建于1991年。它以简洁的语法和丰富的库生态系统著称。"
    
    # 格式化
    formatted = format_knowledge_response(response, knowledge)
    
    print("\n===== 知识库回答格式测试 =====\n")
    print("原始回答:")
    print(response)
    print("\n格式化后:")
    print(formatted)


if __name__ == "__main__":
    test_format() 