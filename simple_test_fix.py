#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试修复后的英译中功能
"""

import requests
import json

def test_simple():
    """简单测试"""
    url = "http://localhost:5000/api/translation/match_terms"
    
    data = {
        "text": "The processes of Neck, Crown, and Body are all crystal growth.",
        "source_lang": "en",
        "target_lang": "zh"
    }
    
    print("测试英译中术语匹配...")
    print(f"文本: {data['text']}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                matched_terms = result.get('matched_terms', [])
                print(f"✓ 成功！找到 {len(matched_terms)} 个术语:")
                
                for term in matched_terms:
                    print(f"  - {term['source']} → {term['target']}")
                
                if len(matched_terms) > 0:
                    print("\n✅ 英译中术语库功能已修复！")
                else:
                    print("\n❌ 仍然没有找到术语，需要进一步调试")
            else:
                print(f"✗ 失败: {result.get('error', '未知错误')}")
        else:
            print(f"✗ HTTP错误: {response.status_code}")
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"✗ 异常: {e}")

if __name__ == "__main__":
    test_simple()
