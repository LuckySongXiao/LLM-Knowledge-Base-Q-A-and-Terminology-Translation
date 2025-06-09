#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的英译中功能
"""

import requests
import json

def test_term_matching(text, source_lang="en", target_lang="zh"):
    """测试术语匹配"""
    url = "http://localhost:5000/api/translation/match_terms"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang
    }
    
    print(f"测试术语匹配: {text}")
    print(f"翻译方向: {source_lang} → {target_lang}")
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
                    if 'position' in term:
                        print(f"    位置: {term['position']}")
                
                return matched_terms
            else:
                print(f"✗ 术语匹配失败: {result.get('error', '未知错误')}")
                return []
        else:
            print(f"✗ API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return []
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return []

def test_translation(text, source_lang="en", target_lang="zh", use_termbase=True):
    """测试翻译"""
    url = "http://localhost:5000/api/translation/translate"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "use_termbase": use_termbase,
        "selected_model": "local_default"
    }
    
    print(f"\n测试翻译: {text}")
    print(f"翻译方向: {source_lang} → {target_lang}")
    print(f"使用术语库: {use_termbase}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                translation_data = result.get('translation', {})
                matched_terms = result.get('matched_terms', [])
                quality_check = result.get('quality_check', {})
                
                print(f"✓ 翻译成功")
                print(f"原文: {translation_data.get('source_text', '')}")
                print(f"译文: {translation_data.get('translated_text', '')}")
                
                if matched_terms:
                    print(f"\n匹配的术语 ({len(matched_terms)} 个):")
                    for term in matched_terms:
                        print(f"  - {term['source']} → {term['target']}")
                else:
                    print(f"\n未找到匹配的术语")
                
                print(f"\n质量检查:")
                print(f"  发现问题: {quality_check.get('issues_found', 0)} 个")
                print(f"  修复问题: {quality_check.get('issues_fixed', 0)} 个")
                remaining_issues = quality_check.get('remaining_issues', [])
                if remaining_issues:
                    print(f"  剩余问题: {remaining_issues}")
                
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

def main():
    """主测试函数"""
    print("测试修复后的英译中功能")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        "The processes of Neck, Crown, and Body are all crystal growth.",
        "Neck growth speed should be carefully controlled.",
        "During the Body stage, maintain stable temperature.",
        "Crown formation requires precise control.",
        "Monocrystal growth involves Neck, Body, and Crown stages.",
        "Polycrystal formation during Diameter measurement."
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试用例 {i}")
        print(f"{'='*60}")
        
        # 1. 先测试术语匹配
        matched_terms = test_term_matching(test_text, "en", "zh")
        
        # 2. 测试翻译（使用术语库）
        result_with_terms = test_translation(test_text, "en", "zh", True)
        
        # 3. 测试翻译（不使用术语库）
        result_without_terms = test_translation(test_text, "en", "zh", False)
        
        print(f"\n对比结果:")
        print(f"使用术语库: {result_with_terms}")
        print(f"不用术语库: {result_without_terms}")
        
        if matched_terms and result_with_terms:
            print("✓ 英译中术语库功能正常")
        elif not matched_terms:
            print("⚠ 未找到匹配术语，可能术语库配置有问题")
        else:
            print("✗ 翻译失败")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
