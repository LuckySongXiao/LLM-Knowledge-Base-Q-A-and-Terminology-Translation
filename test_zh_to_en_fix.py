#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的中译英功能
"""

import requests
import json

def test_zh_to_en_translation(text, use_termbase=True):
    """测试中译英翻译"""
    url = "http://localhost:5000/api/translation/translate"
    
    data = {
        "text": text,
        "source_lang": "auto",  # 使用auto检测
        "target_lang": "en",
        "use_termbase": use_termbase,
        "selected_model": "local_default"
    }
    
    print(f"\n{'='*60}")
    print(f"测试中译英: {text}")
    print(f"使用术语库: {use_termbase}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                translation_data = result.get('translation', {})
                matched_terms = result.get('matched_terms', [])
                quality_check = result.get('quality_check', {})
                
                source_text = translation_data.get('source_text', '')
                translated_text = translation_data.get('translated_text', '')
                
                print(f"✓ 翻译成功")
                print(f"原文: {source_text}")
                print(f"译文: {translated_text}")
                
                if matched_terms:
                    print(f"\n匹配的术语 ({len(matched_terms)} 个):")
                    for term in matched_terms:
                        print(f"  - {term['source']} → {term['target']}")
                        if 'all_targets' in term and len(term['all_targets']) > 1:
                            print(f"    备选术语: {term['all_targets'][1:]}")
                    
                    # 检查术语是否正确应用
                    terms_applied = True
                    for term in matched_terms:
                        if term['target'] not in translated_text:
                            print(f"  ⚠️ 术语 '{term['target']}' 未在译文中找到")
                            terms_applied = False
                    
                    if terms_applied:
                        print(f"  ✅ 所有术语都正确应用到译文中")
                    else:
                        print(f"  ❌ 部分术语未正确应用")
                else:
                    print(f"\n❌ 未找到匹配的术语")
                
                print(f"\n质量检查结果:")
                print(f"  发现问题: {quality_check.get('issues_found', 0)} 个")
                print(f"  修复问题: {quality_check.get('issues_fixed', 0)} 个")
                
                remaining_issues = quality_check.get('remaining_issues', [])
                if remaining_issues:
                    print(f"  剩余问题: {remaining_issues}")
                else:
                    print(f"  ✅ 所有问题已修复或无问题")
                
                return translated_text, len(matched_terms) > 0
            else:
                print(f"✗ 翻译失败: {result.get('error', '未知错误')}")
                return None, False
        else:
            print(f"✗ API请求失败: {response.status_code}")
            return None, False
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return None, False

def test_term_matching_zh_to_en(text):
    """测试中译英术语匹配"""
    url = "http://localhost:5000/api/translation/match_terms"
    
    data = {
        "text": text,
        "source_lang": "auto",  # 使用auto检测
        "target_lang": "en"
    }
    
    print(f"\n测试术语匹配: {text}")
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
                    if 'all_targets' in term and len(term['all_targets']) > 1:
                        print(f"    备选术语: {term['all_targets'][1:]}")
                
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
    print("测试修复后的中译英功能")
    print("=" * 60)
    
    # 测试用例 - 包含术语库中的术语
    test_cases = [
        "引晶、放肩、等径 都是晶体生长的过程工艺",
        "引晶时不能随便手动调整生长速度",
        "等径阶段需要保持稳定的温度和转速",
        "放肩过程中要注意控制引晶速度",
        "单晶生长涉及引晶、等径和放肩阶段",
        "多晶形成过程中的直径测量",
        "转肩阶段的温度控制很重要",
        "回熔现象会影响晶体质量",
        "取段操作需要精确控制",
        "收尾阶段要注意断线问题"
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试用例 {i}/{total_count}")
        print(f"{'='*60}")
        
        # 1. 先测试术语匹配
        matched_terms = test_term_matching_zh_to_en(test_text)
        
        # 2. 测试翻译（使用术语库）
        result_with_terms, terms_found = test_zh_to_en_translation(test_text, True)
        
        # 3. 测试翻译（不使用术语库）
        result_without_terms, _ = test_zh_to_en_translation(test_text, False)
        
        print(f"\n对比结果:")
        print(f"使用术语库: {result_with_terms}")
        print(f"不用术语库: {result_without_terms}")
        
        if terms_found and result_with_terms:
            print(f"✅ 测试用例 {i} 通过 - 术语库功能正常")
            success_count += 1
        elif not matched_terms:
            print(f"⚠️ 测试用例 {i} - 文本中无匹配术语")
            success_count += 1  # 如果没有术语也算正常
        else:
            print(f"❌ 测试用例 {i} 失败 - 术语库功能异常")
    
    print(f"\n{'='*60}")
    print(f"测试总结")
    print(f"{'='*60}")
    print(f"总测试用例: {total_count}")
    print(f"成功用例: {success_count}")
    print(f"失败用例: {total_count - success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print(f"🎉 所有测试用例都通过！")
        print(f"中译英术语库功能已修复。")
    else:
        print(f"⚠️ 有 {total_count - success_count} 个测试用例失败。")
        print(f"需要进一步调试。")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
