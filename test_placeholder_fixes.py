#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试占位符修复功能
"""

import re

def test_placeholder_recovery():
    """测试占位符恢复功能"""
    print("测试占位符恢复功能")
    print("=" * 50)

    test_cases = [
        {
            "name": "中译英占位符变形",
            "translated_text": "_terms_Neck_, _terms_Crown _, and terms_Body are steps in the process of crystal growth.",
            "placeholder_map": {
                "__TERM_001__": "Neck",
                "__TERM_002__": "Crown",
                "__TERM_003__": "Body"
            },
            "expected": "Neck, Crown, and Body are steps in the process of crystal growth."
        },
        {
            "name": "英译中复杂变形",
            "translated_text": "在晶体生长过程中，有三个步骤分别是：__ 引晶、放肩 和 TERML 002。",
            "placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "放肩",
                "__TERM_003__": "等径"
            },
            "expected": "在晶体生长过程中，有三个步骤分别是：引晶、放肩和等径。"
        },
        {
            "name": "英译中带解释文本",
            "translated_text": "在晶体生长过程中，有三个步骤分别是：引晶、放肩 和 TERML 002。不过这里的术语可能需要根据具体上下文进一步解释或确认其含义。",
            "placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "放肩",
                "__TERM_003__": "等径"
            },
            "expected": "在晶体生长过程中，有三个步骤分别是：引晶、放肩和等径。"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        print(f"输入: {test_case['translated_text']}")

        result = simulate_enhanced_recovery(
            test_case['translated_text'],
            test_case['placeholder_map']
        )

        print(f"输出: {result}")
        print(f"期望: {test_case['expected']}")

        if result.strip() == test_case['expected'].strip():
            print("✓ 测试通过")
        else:
            print("✗ 测试失败")

def simulate_enhanced_recovery(translated_text, placeholder_map):
    """模拟增强的占位符恢复过程"""
    result_text = translated_text

    print("  开始占位符恢复...")

    # 第一阶段：精确匹配和模糊匹配
    for placeholder, target_term in placeholder_map.items():
        # 首先尝试精确匹配
        if placeholder in result_text:
            result_text = result_text.replace(placeholder, target_term)
            print(f"    ✓ 精确恢复: '{placeholder}' -> '{target_term}'")
        else:
            # 尝试模糊匹配
            term_number = re.search(r'(\d+)', placeholder)
            if term_number:
                num = int(term_number.group(1))

                # 各种可能的格式变化
                possible_formats = [
                    f"_terms_{target_term}_",  # 直接包含术语名
                    f"_terms {target_term}_",
                    f"terms_{target_term}",
                    f"terms {target_term}",
                    f"_terms_{num}_",
                    f"_terms {num}_",
                    f"terms_{num}",
                    f"terms {num}",
                    f"TERML {num:03d}",  # TERML变形
                    f"TERML {num}",
                    f"__ {target_term}",  # 简化形式
                    f"_terms_Crown _",  # 特殊的空格变形
                ]

                found = False
                for possible_format in possible_formats:
                    if possible_format in result_text:
                        result_text = result_text.replace(possible_format, target_term)
                        print(f"    ✓ 模糊恢复: '{possible_format}' -> '{target_term}'")
                        found = True
                        break

                if not found:
                    print(f"    ✗ 未找到: '{placeholder}' -> '{target_term}'")

    # 第二阶段：清理残留占位符
    print("  开始清理残留占位符...")

    cleanup_patterns = [
        r'_+terms_+\w+_*',
        r'_+terms\s+\w+_*',
        r'terms_+\w+',
        r'terms\s+\w+',
        r'TERML?\s*\d+',
        r'__\s+\w+',
    ]

    for pattern in cleanup_patterns:
        matches = list(re.finditer(pattern, result_text, re.IGNORECASE))
        for match in matches:
            matched_text = match.group()
            print(f"    ⚠ 发现残留: '{matched_text}'")

            # 尝试匹配术语名
            replacement_found = False
            for placeholder, target_term in placeholder_map.items():
                if target_term.lower() in matched_text.lower():
                    result_text = result_text.replace(matched_text, target_term)
                    print(f"    ✓ 清理术语名残留: '{matched_text}' -> '{target_term}'")
                    replacement_found = True
                    break

            if not replacement_found:
                # 删除无法匹配的残留
                result_text = result_text.replace(matched_text, "")
                print(f"    ⚠ 删除无法匹配: '{matched_text}'")

    # 第三阶段：清理解释文本
    print("  开始清理解释文本...")

    explanation_patterns = [
        r'。不过这里的术语可能需要.*',
        r'。如果你能提供更多的背景信息.*',
        r'（注：.*?）',
        r'\(注：.*?\)',
        r'注：.*',
        r'。.*TERMS.*可能是某种.*',
        r'。.*这些代码代表的具体内容.*',
    ]

    for pattern in explanation_patterns:
        if re.search(pattern, result_text):
            original_text = result_text
            result_text = re.sub(pattern, '', result_text)
            if result_text != original_text:
                print(f"    ✓ 移除解释文本: 使用模式 '{pattern[:20]}...'")

    # 第四阶段：清理格式
    print("  开始清理格式...")

    # 清理多余的空格和标点
    result_text = re.sub(r'\s+', ' ', result_text)
    result_text = re.sub(r'\s*([，。！？；：])\s*', r'\1', result_text)
    result_text = re.sub(r'。+', '。', result_text)
    result_text = result_text.strip()

    print(f"  最终结果: {result_text}")
    return result_text

def test_explanation_removal():
    """测试解释文本移除功能"""
    print("\n\n测试解释文本移除功能")
    print("=" * 50)

    test_cases = [
        {
            "name": "标准解释文本",
            "input": "引晶、放肩和等径都是晶体生长工艺。不过这里的术语可能需要根据具体上下文进一步解释或确认其含义。",
            "expected": "引晶、放肩和等径都是晶体生长工艺。"
        },
        {
            "name": "注释形式",
            "input": "引晶、放肩和等径都是晶体生长工艺。（注：TERMS可能是某种特定技术过程中的阶段标识）",
            "expected": "引晶、放肩和等径都是晶体生长工艺。"
        },
        {
            "name": "背景信息请求",
            "input": "引晶、放肩和等径都是晶体生长工艺。如果你能提供更多的背景信息或者这些代码代表的具体内容是什么的话会更好理解。",
            "expected": "引晶、放肩和等径都是晶体生长工艺。"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        print(f"输入: {test_case['input']}")

        result = remove_explanation_text(test_case['input'])

        print(f"输出: {result}")
        print(f"期望: {test_case['expected']}")

        if result.strip() == test_case['expected'].strip():
            print("✓ 测试通过")
        else:
            print("✗ 测试失败")

def remove_explanation_text(text):
    """移除解释文本"""
    result = text

    explanation_patterns = [
        r'。不过这里的术语可能需要.*',
        r'。如果你能提供更多的背景信息.*',
        r'（注：.*?）',
        r'\(注：.*?\)',
        r'注：.*',
        r'。.*TERMS.*可能是某种.*',
        r'。.*这些代码代表的具体内容.*',
    ]

    for pattern in explanation_patterns:
        if re.search(pattern, result):
            result = re.sub(pattern, '', result)

    # 清理格式
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'。+', '。', result)
    result = result.strip()

    return result

if __name__ == "__main__":
    test_placeholder_recovery()
    test_explanation_removal()
    print("\n测试完成！")
