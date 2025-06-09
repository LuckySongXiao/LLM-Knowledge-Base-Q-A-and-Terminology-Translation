#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
思维链处理功能测试脚本
测试AI回答中思维链的检测、处理和显示功能
"""

import sys
import os
import re

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_thinking_chain_detection():
    """测试思维链检测功能"""
    print("=== 测试思维链检测功能 ===")
    
    # 测试用例1：包含单个思维链
    test_case_1 = """
<think>
我需要分析这个问题。首先，我要理解用户的需求...
这个问题涉及到多个方面，我需要逐一分析。
</think>

根据您的问题，我可以提供以下回答：

这是一个很好的问题，需要从多个角度来分析。
"""
    
    # 测试用例2：包含多个思维链
    test_case_2 = """
<think>
第一步思考：分析问题的核心
</think>

首先，让我来分析这个问题。

<think>
第二步思考：考虑解决方案
需要考虑多种可能性...
</think>

基于以上分析，我的建议是...
"""
    
    # 测试用例3：不包含思维链
    test_case_3 = """
这是一个普通的回答，没有思维链。
只是简单的文本内容。
"""
    
    def process_thinking_chain(response):
        """处理AI回答中的思维链，返回处理后的内容"""
        if not response:
            return response
            
        # 检测思维链标签
        think_pattern = r'<think>(.*?)</think>'
        matches = re.findall(think_pattern, response, re.DOTALL)
        
        if not matches:
            return response
            
        # 提取思维链内容和纯净回答
        thinking_content = []
        for match in matches:
            thinking_content.append(match.strip())
        
        # 移除思维链标签，获取纯净回答
        clean_response = re.sub(think_pattern, '', response, flags=re.DOTALL).strip()
        
        # 构建包含折叠思维链的HTML结构
        if thinking_content:
            thinking_html = ""
            for i, think in enumerate(thinking_content):
                thinking_html += f"""
            <div class="thinking-chain-container" data-thinking-id="{i}">
                <div class="thinking-toggle" onclick="toggleThinking({i})">
                    <i class="fas fa-brain"></i> 思维过程 
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <div class="thinking-content collapsed" id="thinking-{i}">
                    <div class="thinking-text">{think}</div>
                </div>
            </div>
            """
            
            # 将思维链插入到回答前面
            processed_response = thinking_html + "\n\n" + clean_response
            return processed_response
        
        return clean_response
    
    # 测试各个用例
    test_cases = [
        ("单个思维链", test_case_1),
        ("多个思维链", test_case_2),
        ("无思维链", test_case_3)
    ]
    
    for name, test_case in test_cases:
        print(f"\n--- 测试用例：{name} ---")
        print("原始内容：")
        print(test_case[:100] + "..." if len(test_case) > 100 else test_case)
        
        processed = process_thinking_chain(test_case)
        
        print("\n处理后内容：")
        print(processed[:200] + "..." if len(processed) > 200 else processed)
        
        # 检查是否包含思维链容器
        has_thinking_container = "thinking-chain-container" in processed
        print(f"包含思维链容器：{has_thinking_container}")
        
        # 检查纯净内容提取
        clean_pattern = r'<div class="thinking-chain-container".*?</div>\s*'
        clean_content = re.sub(clean_pattern, '', processed, flags=re.DOTALL).strip()
        print(f"纯净内容长度：{len(clean_content)}")

def test_copy_functionality():
    """测试复制功能的纯净内容提取"""
    print("\n=== 测试复制功能 ===")
    
    # 模拟包含思维链的HTML内容
    html_content = """
    <div class="thinking-chain-container" data-thinking-id="0">
        <div class="thinking-toggle">思维过程</div>
        <div class="thinking-content">这是思维链内容</div>
    </div>
    
    这是实际的回答内容，用户应该能够复制这部分。
    """
    
    def extract_clean_text(html_content):
        """从HTML内容中提取纯净文本（移除思维链）"""
        # 移除思维链容器
        clean_pattern = r'<div class="thinking-chain-container".*?</div>'
        clean_content = re.sub(clean_pattern, '', html_content, flags=re.DOTALL)
        
        # 移除HTML标签
        tag_pattern = r'<[^>]+>'
        clean_text = re.sub(tag_pattern, '', clean_content)
        
        # 清理多余的空白字符
        clean_text = re.sub(r'\n\s*\n', '\n', clean_text).strip()
        
        return clean_text
    
    clean_text = extract_clean_text(html_content)
    print("原始HTML内容：")
    print(html_content)
    print("\n提取的纯净文本：")
    print(repr(clean_text))
    print("\n纯净文本内容：")
    print(clean_text)

def test_model_resource_management():
    """测试模型资源管理逻辑"""
    print("\n=== 测试模型资源管理逻辑 ===")
    
    # 模拟模型类型检测
    def detect_model_type(selected_model):
        """检测模型类型"""
        if selected_model.startswith('openai_'):
            return 'openai'
        elif selected_model.startswith('ollama_') or selected_model in ['llama2', 'qwen', 'chatglm']:
            return 'ollama'
        else:
            return 'local'
    
    # 测试不同模型的类型检测
    test_models = [
        'local_default',
        'openai_deepseek-r1-70b',
        'ollama_llama2',
        'qwen',
        'chatglm'
    ]
    
    for model in test_models:
        model_type = detect_model_type(model)
        print(f"模型 '{model}' -> 类型: {model_type}")
    
    # 模拟资源管理决策
    current_type = 'local'
    for model in test_models:
        new_type = detect_model_type(model)
        
        if current_type != new_type:
            if current_type == 'local' and new_type != 'local':
                print(f"切换 {current_type} -> {new_type}: 需要卸载本地模型")
            elif current_type != 'local' and new_type == 'local':
                print(f"切换 {current_type} -> {new_type}: 需要重新加载本地模型")
            else:
                print(f"切换 {current_type} -> {new_type}: 无需特殊处理")
        else:
            print(f"保持 {current_type}: 无需处理")
        
        current_type = new_type

if __name__ == "__main__":
    print("思维链处理功能测试")
    print("=" * 50)
    
    try:
        test_thinking_chain_detection()
        test_copy_functionality()
        test_model_resource_management()
        
        print("\n" + "=" * 50)
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
