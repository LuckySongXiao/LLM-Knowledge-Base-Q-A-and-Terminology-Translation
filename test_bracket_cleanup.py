#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试括号清理功能
"""

import re

def test_bracket_cleanup():
    """测试术语括号清理功能"""
    print("测试术语括号清理功能")
    print("=" * 40)

    test_cases = [
        {
            "name": "基本括号清理",
            "input": "(引晶)、(放肩)和(等径)都是晶体生长工艺。",
            "placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "放肩",
                "__TERM_003__": "等径"
            },
            "expected": "引晶、放肩和等径都是晶体生长工艺。"
        },
        {
            "name": "混合括号清理",
            "input": "在(引晶)阶段，需要控制放肩的速度和(等径)的温度。",
            "placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "放肩",
                "__TERM_003__": "等径"
            },
            "expected": "在引晶阶段，需要控制放肩的速度和等径的温度。"
        },
        {
            "name": "行首行末括号",
            "input": "(引晶)是第一个阶段，最后是(等径)",
            "placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "等径"
            },
            "expected": "引晶是第一个阶段，最后是等径"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 30)
        print(f"输入: {test_case['input']}")

        result = clean_term_brackets(test_case['input'], test_case['placeholder_map'])

        print(f"输出: {result}")
        print(f"期望: {test_case['expected']}")

        if result == test_case['expected']:
            print("✓ 测试通过")
        else:
            print("✗ 测试失败")

def clean_term_brackets(text, placeholder_map):
    """清理术语周围的括号"""
    result_text = text

    # 清理术语周围的多余括号
    for placeholder, target_term in placeholder_map.items():
        # 简化的括号清理：直接替换 (术语) 为 术语
        pattern = rf'\(\s*{re.escape(target_term)}\s*\)'

        if re.search(pattern, result_text):
            result_text = re.sub(pattern, target_term, result_text)
            print(f"  ✓ 清理术语括号: '({target_term})' -> '{target_term}'")

    return result_text

if __name__ == "__main__":
    test_bracket_cleanup()
