#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EN→ZH反向翻译术语库测试脚本
测试反向术语库缓存和占位符机制
"""

import requests
import json
import time

# WEB API 基础URL
BASE_URL = "http://localhost:5000"

def test_reverse_translation(text, source_lang="en", target_lang="zh", use_termbase=True, selected_model="local_default"):
    """测试EN→ZH反向翻译"""
    url = f"{BASE_URL}/api/translation/translate"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "use_termbase": use_termbase,
        "selected_model": selected_model
    }
    
    print(f"\n{'='*60}")
    print(f"测试反向翻译: {text}")
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
                    print(f"\n匹配的反向术语 ({len(matched_terms)} 个):")
                    for term in matched_terms:
                        print(f"  - {term['source']} → {term['target']}")
                else:
                    print(f"\n未找到匹配的术语")
                
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

def test_reverse_term_matching(text, source_lang="en", target_lang="zh"):
    """测试反向术语匹配"""
    url = f"{BASE_URL}/api/translation/match_terms"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang
    }
    
    print(f"\n{'='*40}")
    print(f"测试反向术语匹配: {text}")
    print(f"翻译方向: {source_lang} → {target_lang}")
    print(f"{'='*40}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                matched_terms = result.get('matched_terms', [])
                print(f"✓ 反向术语匹配成功，找到 {len(matched_terms)} 个术语:")
                
                for term in matched_terms:
                    print(f"  - {term['source']} → {term['target']} (位置: {term.get('position', 'N/A')})")
                
                return matched_terms
            else:
                print(f"✗ 反向术语匹配失败: {result.get('error', '未知错误')}")
                return []
        else:
            print(f"✗ API请求失败: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return []

def main():
    """主测试函数"""
    print("EN→ZH反向翻译术语库测试")
    print("=" * 60)
    
    # EN→ZH测试用例
    en_to_zh_test_cases = [
        {
            "text": "The neck growth speed should be carefully controlled",
            "description": "包含Neck术语的英译中测试",
            "expected_terms": ["Neck"]
        },
        {
            "text": "During the body stage, maintain stable temperature and rotation speed",
            "description": "包含Body术语的英译中测试", 
            "expected_terms": ["Body"]
        },
        {
            "text": "The crown process requires attention to neck speed control",
            "description": "包含多个术语的英译中测试",
            "expected_terms": ["Crown", "Neck"]
        },
        {
            "text": "Monocrystal growth involves neck, body, and crown stages",
            "description": "包含多个术语的复合测试",
            "expected_terms": ["Monocrystal", "Neck", "Body", "Crown"]
        },
        {
            "text": "The diameter measurement during polycrystal formation",
            "description": "包含Diameter和Polycrystal术语的测试",
            "expected_terms": ["Diameter", "Polycrystal"]
        }
    ]
    
    print("\n开始EN→ZH反向翻译测试...")
    
    # 执行测试
    for i, test_case in enumerate(en_to_zh_test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['description']}")
        print(f"期望术语: {test_case['expected_terms']}")
        
        # 先测试反向术语匹配
        matched_terms = test_reverse_term_matching(
            test_case['text'], 
            "en", 
            "zh"
        )
        
        # 验证是否找到了期望的术语
        found_terms = [term['source'] for term in matched_terms]
        expected_terms = test_case['expected_terms']
        
        print(f"\n术语匹配验证:")
        for expected_term in expected_terms:
            if any(expected_term.lower() in found_term.lower() for found_term in found_terms):
                print(f"  ✓ 找到期望术语: {expected_term}")
            else:
                print(f"  ✗ 未找到期望术语: {expected_term}")
        
        # 测试完整的EN→ZH翻译
        result = test_reverse_translation(
            test_case['text'],
            "en",
            "zh",
            use_termbase=True,
            selected_model="local_default"
        )
        
        time.sleep(1)  # 避免请求过快
    
    # 对比测试：不使用术语库的翻译
    print(f"\n{'='*60}")
    print("对比测试：不使用术语库的EN→ZH翻译")
    print(f"{'='*60}")
    
    test_text = "The neck growth speed should be carefully controlled"
    
    print("\n1. 使用术语库的翻译:")
    result_with_terms = test_reverse_translation(
        test_text, "en", "zh", use_termbase=True
    )
    
    print("\n2. 不使用术语库的翻译:")
    result_without_terms = test_reverse_translation(
        test_text, "en", "zh", use_termbase=False
    )
    
    print(f"\n对比结果:")
    print(f"使用术语库: {result_with_terms}")
    print(f"不用术语库: {result_without_terms}")
    
    print(f"\n{'='*60}")
    print("EN→ZH反向翻译测试完成！")
    print("请检查上述结果，验证反向术语库机制是否正常工作。")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
