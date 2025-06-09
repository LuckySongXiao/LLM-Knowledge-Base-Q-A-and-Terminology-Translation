#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强的占位符清理机制
"""

import requests
import json

def test_translation_with_cleanup(text, source_lang="en", target_lang="zh", use_termbase=True):
    """测试翻译和占位符清理"""
    url = "http://localhost:5000/api/translation/translate"
    
    data = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "use_termbase": use_termbase,
        "selected_model": "local_default"
    }
    
    print(f"\n{'='*60}")
    print(f"测试文本: {text}")
    print(f"翻译方向: {source_lang} → {target_lang}")
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
                
                # 检查是否有占位符残留
                import re
                placeholder_patterns = [
                    r'__+\s*TERM\s*_?\s*\d+\s*_*__+',
                    r'__+\s*Term\s*_?\s*\d+\s*_*__+',
                    r'\[\s*TERM\s*_?\s*\d+\s*\]',
                    r'TERM\s*_?\s*\d+',
                    r'Term\s*_?\s*\d+',
                    r'__+\d+__+',
                    r'_+TERM_+\d+_+',
                    r'_+Term_+\d+_+'
                ]
                
                placeholder_found = False
                for pattern in placeholder_patterns:
                    matches = re.findall(pattern, translated_text, re.IGNORECASE)
                    if matches:
                        print(f"❌ 发现占位符残留: {matches}")
                        placeholder_found = True
                
                if not placeholder_found:
                    print(f"✅ 无占位符残留，清理成功！")
                
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
                    # 检查是否有占位符相关问题
                    placeholder_issues = [issue for issue in remaining_issues if '占位符' in issue or 'TERM' in issue]
                    if placeholder_issues:
                        print(f"  ❌ 占位符问题: {placeholder_issues}")
                    else:
                        print(f"  ✅ 无占位符相关问题")
                else:
                    print(f"  ✅ 所有问题已修复或无问题")
                
                return translated_text, not placeholder_found
            else:
                print(f"✗ 翻译失败: {result.get('error', '未知错误')}")
                return None, False
        else:
            print(f"✗ API请求失败: {response.status_code}")
            return None, False
            
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return None, False

def main():
    """主测试函数"""
    print("增强占位符清理机制测试")
    print("=" * 60)
    
    # 测试用例 - 这些文本容易产生占位符残留
    test_cases = [
        "The processes of Neck, Crown, and Body are all crystal growth.",
        "Neck growth speed should be carefully controlled.",
        "During the Body stage, maintain stable temperature.",
        "Crown formation requires precise control.",
        "Monocrystal growth involves Neck, Body, and Crown stages.",
        "Polycrystal formation during Diameter measurement.",
        "The Neck and Body sections need careful monitoring.",
        "Crown and Shoulder transitions are critical.",
        "Melted back occurs during the Tail formation.",
        "Pop-out process affects the final Diameter."
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试用例 {i}/{total_count}")
        print(f"{'='*60}")
        
        result, cleanup_success = test_translation_with_cleanup(test_text, "en", "zh", True)
        
        if cleanup_success:
            success_count += 1
            print(f"✅ 测试用例 {i} 通过")
        else:
            print(f"❌ 测试用例 {i} 失败")
    
    print(f"\n{'='*60}")
    print(f"测试总结")
    print(f"{'='*60}")
    print(f"总测试用例: {total_count}")
    print(f"成功清理: {success_count}")
    print(f"失败清理: {total_count - success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print(f"🎉 所有测试用例都成功清理了占位符！")
        print(f"增强的占位符清理机制工作正常。")
    else:
        print(f"⚠️ 有 {total_count - success_count} 个测试用例仍有占位符残留。")
        print(f"需要进一步优化清理机制。")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
