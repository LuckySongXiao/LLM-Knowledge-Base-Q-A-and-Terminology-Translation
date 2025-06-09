#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的EN→ZH反向翻译测试
"""

import requests
import json

def test_single_translation():
    """测试单个EN→ZH翻译"""
    url = "http://localhost:5000/api/translation/translate"
    
    data = {
        "text": "The neck growth speed should be carefully controlled",
        "source_lang": "en",
        "target_lang": "zh",
        "use_termbase": True,
        "selected_model": "local_default"
    }
    
    print("测试EN→ZH反向翻译")
    print(f"原文: {data['text']}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                translation_data = result.get('translation', {})
                matched_terms = result.get('matched_terms', [])
                
                print("✓ 翻译成功")
                print(f"译文: {translation_data.get('translated_text', '')}")
                
                if matched_terms:
                    print(f"\n匹配的术语 ({len(matched_terms)} 个):")
                    for term in matched_terms:
                        print(f"  - {term['source']} → {term['target']}")
                else:
                    print("\n未找到匹配的术语")
                
                return True
            else:
                print(f"✗ 翻译失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"✗ API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return False

def test_term_matching():
    """测试术语匹配"""
    url = "http://localhost:5000/api/translation/match_terms"
    
    data = {
        "text": "The neck growth speed should be carefully controlled",
        "source_lang": "en",
        "target_lang": "zh"
    }
    
    print("\n测试术语匹配")
    print(f"文本: {data['text']}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                matched_terms = result.get('matched_terms', [])
                print(f"✓ 术语匹配成功，找到 {len(matched_terms)} 个术语:")
                
                for term in matched_terms:
                    print(f"  - {term['source']} → {term['target']}")
                
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

if __name__ == "__main__":
    print("简化的EN→ZH反向翻译测试")
    print("=" * 60)
    
    # 先测试术语匹配
    matched_terms = test_term_matching()
    
    # 再测试完整翻译
    success = test_single_translation()
    
    print("\n" + "=" * 60)
    if success and matched_terms:
        print("✓ 反向翻译功能正常工作")
    elif success:
        print("⚠ 翻译成功但术语匹配可能有问题")
    else:
        print("✗ 反向翻译功能存在问题")
    print("=" * 60)
