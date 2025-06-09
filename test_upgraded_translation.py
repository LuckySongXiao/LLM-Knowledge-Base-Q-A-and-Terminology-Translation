#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
升级版翻译系统测试脚本
测试多术语支持和增强的占位符恢复机制
"""

import requests
import json
import time

# WEB API 基础URL
BASE_URL = "http://localhost:5000"

def test_multiple_terms_parsing():
    """测试多术语解析功能"""
    print("=" * 60)
    print("测试多术语解析功能")
    print("=" * 60)
    
    test_cases = [
        "Neck,Crystal neck,Growth neck",
        "Body,Constant diameter,Cylindrical section", 
        "polycrystal,polycrystalline,multi-crystal",
        "monocrystal,single crystal,monocrystalline"
    ]
    
    for term_string in test_cases:
        terms = [term.strip() for term in term_string.split(',') if term.strip()]
        print(f"原始术语字符串: {term_string}")
        print(f"解析结果: {terms}")
        print(f"主要术语（最高优先级）: {terms[0] if terms else '无'}")
        print(f"备用术语: {terms[1:] if len(terms) > 1 else '无'}")
        print("-" * 40)

def test_translation_with_multiple_terms(text, source_lang="zh", target_lang="en", use_termbase=True):
    """测试支持多术语的翻译"""
    url = f"{BASE_URL}/api/translation/translate"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "use_termbase": use_termbase,
        "selected_model": "local_default"
    }
    
    print(f"\n{'='*60}")
    print(f"测试多术语翻译: {text}")
    print(f"翻译方向: {source_lang} → {target_lang}")
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
                        if 'all_targets' in term and len(term['all_targets']) > 1:
                            print(f"    备用术语: {term['all_targets'][1:]}")
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

def test_reverse_translation_with_multiple_terms(text, source_lang="en", target_lang="zh", use_termbase=True):
    """测试EN→ZH反向翻译的多术语支持"""
    url = f"{BASE_URL}/api/translation/translate"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "use_termbase": use_termbase,
        "selected_model": "local_default"
    }
    
    print(f"\n{'='*60}")
    print(f"测试反向多术语翻译: {text}")
    print(f"翻译方向: {source_lang} → {target_lang}")
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
            return None
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return None

def main():
    """主测试函数"""
    print("升级版翻译系统测试")
    print("=" * 60)
    
    # 1. 测试多术语解析
    test_multiple_terms_parsing()
    
    # 2. 测试ZH→EN翻译（多术语支持）
    print("\n" + "=" * 60)
    print("测试ZH→EN翻译（多术语支持）")
    print("=" * 60)
    
    zh_to_en_cases = [
        "引晶时不能随便手动调整生长速度",
        "等径阶段需要保持稳定的温度和转速", 
        "放肩过程中要注意控制引晶速度",
        "单晶生长涉及引晶、等径和放肩阶段",
        "多晶形成过程中的直径测量"
    ]
    
    for case in zh_to_en_cases:
        result = test_translation_with_multiple_terms(case, "zh", "en", True)
        time.sleep(1)
    
    # 3. 测试EN→ZH反向翻译（多术语支持）
    print("\n" + "=" * 60)
    print("测试EN→ZH反向翻译（多术语支持）")
    print("=" * 60)
    
    en_to_zh_cases = [
        "The neck growth speed should be carefully controlled",
        "During the body stage, maintain stable temperature",
        "Crystal neck formation requires precise control",
        "Monocrystal growth involves neck, body, and crown stages",
        "Polycrystalline formation during diameter measurement",
        "Single crystal growth with constant diameter section"
    ]
    
    for case in en_to_zh_cases:
        result = test_reverse_translation_with_multiple_terms(case, "en", "zh", True)
        time.sleep(1)
    
    # 4. 对比测试：使用术语库 vs 不使用术语库
    print("\n" + "=" * 60)
    print("对比测试：术语库效果对比")
    print("=" * 60)
    
    test_text = "The monocrystal neck growth speed should be carefully controlled during the body stage"
    
    print("\n1. 使用升级版术语库:")
    result_with_terms = test_reverse_translation_with_multiple_terms(test_text, "en", "zh", True)
    
    print("\n2. 不使用术语库:")
    result_without_terms = test_reverse_translation_with_multiple_terms(test_text, "en", "zh", False)
    
    print(f"\n对比结果:")
    print(f"使用术语库: {result_with_terms}")
    print(f"不用术语库: {result_without_terms}")
    
    print(f"\n{'='*60}")
    print("升级版翻译系统测试完成！")
    print("主要改进:")
    print("1. ✓ 支持多个外语术语（用逗号分隔）")
    print("2. ✓ 术语优先级机制（第一个术语享有最高权限）")
    print("3. ✓ 增强的占位符恢复机制")
    print("4. ✓ 强制恢复和残留清理功能")
    print("5. ✓ 双向翻译术语一致性")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
