#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译质量自查机制测试脚本
测试新的翻译质量验证和修复功能
"""

import requests
import json
import time

# WEB API 基础URL
BASE_URL = "http://localhost:5000"

def test_translation_api(text, source_lang="zh", target_lang="en", use_termbase=True, selected_model="local_default"):
    """测试翻译API"""
    url = f"{BASE_URL}/api/translation/translate"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "use_termbase": use_termbase,
        "selected_model": selected_model
    }
    
    print(f"\n{'='*60}")
    print(f"测试翻译: {text}")
    print(f"翻译方向: {source_lang} → {target_lang}")
    print(f"使用术语库: {use_termbase}")
    print(f"选择模型: {selected_model}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                translation_data = result.get('translation', {})
                quality_check = result.get('quality_check', {})
                matched_terms = result.get('matched_terms', [])
                
                print(f"✓ 翻译成功")
                print(f"原文: {translation_data.get('source_text', '')}")
                print(f"译文: {translation_data.get('translated_text', '')}")
                
                if matched_terms:
                    print(f"\n匹配的术语 ({len(matched_terms)} 个):")
                    for term in matched_terms:
                        print(f"  - {term['source']} → {term['target']}")
                
                print(f"\n质量检查结果:")
                print(f"  发现问题: {quality_check.get('issues_found', 0)} 个")
                print(f"  修复问题: {quality_check.get('issues_fixed', 0)} 个")
                
                remaining_issues = quality_check.get('remaining_issues', [])
                if remaining_issues:
                    print(f"  剩余问题: {remaining_issues}")
                else:
                    print(f"  ✓ 所有问题已修复或无问题")
                
                return translation_data.get('translated_text', '')
            else:
                print(f"✗ 翻译失败: {result.get('error', '未知错误')}")
                return None
        else:
            print(f"✗ API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return None

def test_term_matching(text, source_lang="zh", target_lang="en"):
    """测试术语匹配"""
    url = f"{BASE_URL}/api/translation/match_terms"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang
    }
    
    print(f"\n{'='*40}")
    print(f"测试术语匹配: {text}")
    print(f"{'='*40}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                matched_terms = result.get('matched_terms', [])
                print(f"✓ 术语匹配成功，找到 {len(matched_terms)} 个术语:")
                
                for term in matched_terms:
                    print(f"  - {term['source']} → {term['target']} (位置: {term.get('position', 'N/A')})")
                
                return matched_terms
            else:
                print(f"✗ 术语匹配失败: {result.get('error', '未知错误')}")
                return []
        else:
            print(f"✗ API请求失败: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return []

def main():
    """主测试函数"""
    print("翻译质量自查机制测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "text": "引晶时不能随便手动调整生长速度",
            "description": "包含术语的基本翻译测试",
            "source_lang": "zh",
            "target_lang": "en"
        },
        {
            "text": "等径阶段需要保持稳定的温度和转速",
            "description": "多术语翻译测试",
            "source_lang": "zh", 
            "target_lang": "en"
        },
        {
            "text": "放肩过程中要注意控制引晶速度",
            "description": "复合术语翻译测试",
            "source_lang": "zh",
            "target_lang": "en"
        },
        {
            "text": "The neck growth speed should be carefully controlled",
            "description": "英译中测试",
            "source_lang": "en",
            "target_lang": "zh"
        }
    ]
    
    # 执行测试
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['description']}")
        
        # 先测试术语匹配
        matched_terms = test_term_matching(
            test_case['text'], 
            test_case['source_lang'], 
            test_case['target_lang']
        )
        
        # 测试翻译（使用本地模型）
        result = test_translation_api(
            test_case['text'],
            test_case['source_lang'],
            test_case['target_lang'],
            use_termbase=True,
            selected_model="local_default"
        )
        
        time.sleep(1)  # 避免请求过快
    
    print(f"\n{'='*60}")
    print("测试完成！")
    print("请检查上述结果，验证翻译质量自查机制是否正常工作。")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
