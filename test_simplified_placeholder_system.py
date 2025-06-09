#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试简化的占位符系统
"""

import re

def test_simplified_placeholder_system():
    """测试简化的占位符系统"""
    print("测试简化的占位符系统")
    print("=" * 60)

    # 模拟术语库
    terms = [
        {'source': '引晶', 'target': 'Neck'},
        {'source': '放肩', 'target': 'Crown'},
        {'source': '等径', 'target': 'Body'},
        {'source': '转肩', 'target': 'Shoulder'}
    ]

    test_cases = [
        {
            "name": "中译英测试",
            "source_text": "引晶、放肩、等径都是晶体生长的过程工艺步骤",
            "source_lang": "zh",
            "target_lang": "en",
            "expected_placeholders": "[T1]、[T2]、[T3]都是晶体生长的过程工艺步骤",
            "expected_final": "Neck, Crown, and Body are crystal growth process steps"
        },
        {
            "name": "英译中测试",
            "source_text": "Neck, Crown, and Body are steps in the process of crystal growth.",
            "source_lang": "en",
            "target_lang": "zh",
            "expected_placeholders": "[T1], [T2], and [T3] are steps in the process of crystal growth.",
            "expected_final": "引晶、放肩和等径是晶体生长过程中的步骤。"
        },
        {
            "name": "包含四个术语的测试",
            "source_text": "Neck, Crown, Shoulder and Body are steps in the process of crystal growth.",
            "source_lang": "en",
            "target_lang": "zh",
            "expected_placeholders": "[T1], [T2], [T3] and [T4] are steps in the process of crystal growth.",
            "expected_final": "引晶、放肩、转肩和等径是晶体生长过程中的步骤。"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 50)
        print(f"原文: {test_case['source_text']}")

        # 第一步：术语匹配和占位符替换
        matched_terms, placeholder_map = simulate_term_replacement(
            test_case['source_text'],
            terms,
            test_case['source_lang'],
            test_case['target_lang']
        )

        print(f"匹配术语: {len(matched_terms)} 个")
        for term in matched_terms:
            print(f"  {term['source']} -> {term['target']}")

        print(f"占位符映射: {placeholder_map}")

        # 第二步：创建带占位符的文本
        text_with_placeholders = test_case['source_text']
        for i, term in enumerate(matched_terms):
            text_with_placeholders = text_with_placeholders.replace(term['source'], f"[T{i+1}]")

        # 模拟翻译过程
        translated_with_placeholders = simulate_translation(
            text_with_placeholders,
            test_case['source_lang'],
            test_case['target_lang']
        )

        print(f"翻译结果（含占位符）: {translated_with_placeholders}")

        # 第三步：占位符恢复
        final_result = simulate_placeholder_restoration(
            translated_with_placeholders,
            placeholder_map
        )

        print(f"最终结果: {final_result}")
        print(f"期望结果: {test_case['expected_final']}")

        # 验证结果
        if all(term['target'] in final_result for term in matched_terms):
            print("✓ 术语恢复成功")
        else:
            print("✗ 术语恢复失败")

def simulate_term_replacement(text, terms, source_lang, target_lang):
    """模拟术语替换过程"""
    matched_terms = []
    placeholder_map = {}

    # 根据翻译方向匹配术语
    for term in terms:
        if source_lang == 'zh' and target_lang == 'en':
            # 中译英：匹配中文术语
            if term['source'] in text:
                matched_terms.append(term)
        elif source_lang == 'en' and target_lang == 'zh':
            # 英译中：匹配英文术语
            if term['target'] in text:
                # 创建反向映射
                matched_terms.append({
                    'source': term['target'],  # 英文作为源
                    'target': term['source']   # 中文作为目标
                })

    # 创建占位符映射
    for i, term in enumerate(matched_terms, 1):
        placeholder = f"[T{i}]"
        placeholder_map[placeholder] = term['target']

    return matched_terms, placeholder_map

def simulate_translation(text, source_lang, target_lang):
    """模拟翻译过程（简化版）"""
    # 这里只是模拟，实际中会调用翻译模型
    if source_lang == 'zh' and target_lang == 'en':
        # 中译英模拟
        if "[T1]、[T2]、[T3]都是晶体生长的过程工艺步骤" in text:
            return "[T1], [T2], and [T3] are crystal growth process steps"
    elif source_lang == 'en' and target_lang == 'zh':
        # 英译中模拟
        if "[T1], [T2], and [T3] are steps" in text:
            return "[T1]、[T2]和[T3]是晶体生长过程中的步骤。"
        elif "[T1], [T2], [T3] and [T4] are steps" in text:
            return "[T1]、[T2]、[T3]和[T4]是晶体生长过程中的步骤。"

    return text  # 如果没有匹配的模拟，返回原文

def simulate_placeholder_restoration(text, placeholder_map):
    """模拟占位符恢复过程"""
    result = text

    print(f"  开始恢复占位符...")

    # 第一阶段：精确匹配
    for placeholder, target_term in placeholder_map.items():
        if placeholder in result:
            result = result.replace(placeholder, target_term)
            print(f"    ✓ 精确恢复: {placeholder} -> {target_term}")

    # 第二阶段：处理简单变形
    for placeholder, target_term in placeholder_map.items():
        # 提取数字
        num_match = re.search(r'T(\d+)', placeholder)
        if num_match:
            num = num_match.group(1)

            # 常见变形
            variants = [
                f"[T {num}]",      # 空格变形
                f"[ T{num} ]",     # 前后空格
                f"[ T {num} ]",    # 完全空格
                f"T{num}",         # 无括号
                f"T {num}",        # 无括号+空格
            ]

            for variant in variants:
                if variant in result:
                    result = result.replace(variant, target_term)
                    print(f"    ✓ 变形恢复: {variant} -> {target_term}")

    # 第三阶段：清理任何残留
    cleanup_patterns = [
        r'\[T\s*\d+\s*\]',
        r'T\s*\d+',
    ]

    for pattern in cleanup_patterns:
        matches = re.findall(pattern, result)
        for match in matches:
            print(f"    ⚠ 发现残留: {match}")
            result = result.replace(match, "")

    # 清理格式
    result = re.sub(r'\s+', ' ', result)
    result = result.strip()

    print(f"  恢复完成: {result}")
    return result

def test_quality_validation():
    """测试质量验证"""
    print("\n\n测试质量验证")
    print("=" * 60)

    test_cases = [
        {
            "name": "正常翻译",
            "translated": "引晶、放肩和等径是晶体生长过程中的步骤。",
            "placeholder_map": {},
            "expected_issues": 0
        },
        {
            "name": "占位符残留",
            "translated": "引晶、放肩和[T3]是晶体生长过程中的步骤。",
            "placeholder_map": {"[T3]": "等径"},
            "expected_issues": 1
        },
        {
            "name": "解释文本",
            "translated": "引晶、放肩和等径是步骤。不过这里的术语可能需要根据具体上下文进一步解释。",
            "placeholder_map": {},
            "expected_issues": 1
        },
        {
            "name": "复杂残留格式",
            "translated": "引晶、放肩、TER M 001 和 TERMINOLOGY 003是步骤。",
            "placeholder_map": {"[T1]": "引晶", "[T2]": "放肩"},
            "expected_issues": 1
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        print(f"译文: {test_case['translated']}")

        issues = simulate_quality_validation(
            test_case['translated'],
            test_case['placeholder_map']
        )

        print(f"发现问题: {len(issues)} 个")
        for issue in issues:
            print(f"  - {issue}")

        if len(issues) == test_case['expected_issues']:
            print("✓ 验证通过")
        else:
            print(f"✗ 验证失败，期望 {test_case['expected_issues']} 个问题")

def simulate_quality_validation(translated_text, placeholder_map):
    """模拟质量验证"""
    issues = []

    # 检查占位符残留
    if placeholder_map:
        # 检查原始占位符
        for placeholder in placeholder_map.keys():
            if placeholder in translated_text:
                issues.append(f"占位符未恢复: {placeholder}")

        # 检查残留格式
        patterns = [
            r'\[T\s*\d+\s*\]',
            r'T\s*\d+',
            r'TER\s*M\s*\d+',
            r'TERMINOLOGY\s*\d+',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, translated_text, re.IGNORECASE)
            if matches:
                issues.append(f"发现占位符残留: {matches}")

    # 检查解释文本
    explanation_indicators = [
        '不过这里的术语可能需要',
        '如果你能提供更多的背景信息',
        '注：',
        '这里的术语似乎是',
        '请根据具体情境理解',
    ]

    for indicator in explanation_indicators:
        if indicator in translated_text:
            issues.append(f"翻译结果包含解释文本: 包含'{indicator}'")
            break

    return issues

if __name__ == "__main__":
    test_simplified_placeholder_system()
    test_quality_validation()
    print("\n测试完成！")
