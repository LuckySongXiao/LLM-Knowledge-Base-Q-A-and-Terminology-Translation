#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试最终的占位符修复功能
"""

import re

def test_final_cleanup():
    """测试最终清理功能"""
    print("测试最终占位符清理功能")
    print("=" * 50)

    test_cases = [
        {
            "name": "英译中单独双下划线残留",
            "input": "在晶体生长过程中，有三个步骤分别是：__ 引晶、放肩 和 等径",
            "placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "放肩",
                "__TERM_003__": "等径"
            },
            "expected": "在晶体生长过程中，有三个步骤分别是：引晶、放肩和等径"
        },
        {
            "name": "中译英术语名+下划线残留",
            "input": "Crown, Crown _, and Body are steps in the process of crystal growth.",
            "placeholder_map": {
                "__TERM_001__": "Neck",
                "__TERM_002__": "Crown",
                "__TERM_003__": "Body"
            },
            "expected": "Crown, Crown, and Body are steps in the process of crystal growth."
        },
        {
            "name": "复杂残留格式",
            "input": "The _terms_Neck_, Crown _ and Body are important stages.",
            "placeholder_map": {
                "__TERM_001__": "Neck",
                "__TERM_002__": "Crown",
                "__TERM_003__": "Body"
            },
            "expected": "The Neck, Crown and Body are important stages."
        },
        {
            "name": "TERML格式残留",
            "input": "引晶、放肩和TERML 002是重要步骤。",
            "placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "放肩",
                "__TERM_003__": "等径"
            },
            "expected": "引晶、放肩和等径是重要步骤。"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        print(f"输入: {test_case['input']}")

        result = simulate_final_cleanup(
            test_case['input'],
            test_case['placeholder_map']
        )

        print(f"输出: {result}")
        print(f"期望: {test_case['expected']}")

        if result.strip() == test_case['expected'].strip():
            print("✓ 测试通过")
        else:
            print("✗ 测试失败")

def simulate_final_cleanup(text, placeholder_map):
    """模拟最终清理过程"""
    result_text = text

    print("  开始最终清理...")

    # 第一阶段：处理已知的占位符变形
    cleanup_patterns = [
        r'_+terms_+\w+_*',
        r'_+terms\s+\w+_*',
        r'terms_+\w+',
        r'terms\s+\w+',
        r'TERML?\s*\d+',
        r'__\s*$',
        r'__\s+',
        r'\s+__\s*',
        r'[A-Za-z]+\s+_\s*',
        r'_\s+[A-Za-z]+',
        r'[A-Za-z]+\s*_+\s*$',
    ]

    for pattern in cleanup_patterns:
        matches = list(re.finditer(pattern, result_text, re.IGNORECASE))
        for match in matches:
            matched_text = match.group()
            print(f"    发现残留: '{matched_text}'")

            # 尝试匹配术语名
            replacement_found = False

            # 首先尝试提取数字
            num_match = re.search(r'(\d+)', matched_text)
            if num_match:
                num = int(num_match.group(1))
                # 根据数字找到对应的占位符
                target_placeholder = f"__TERM_{num:03d}__"
                if target_placeholder in placeholder_map:
                    target_term = placeholder_map[target_placeholder]
                    result_text = result_text.replace(matched_text, target_term)
                    print(f"    ✓ 数字匹配恢复: '{matched_text}' -> '{target_term}'")
                    replacement_found = True

            # 如果没有找到数字，尝试直接匹配术语名
            if not replacement_found:
                for placeholder, target_term in placeholder_map.items():
                    if target_term.lower() in matched_text.lower():
                        result_text = result_text.replace(matched_text, target_term)
                        print(f"    ✓ 术语名匹配恢复: '{matched_text}' -> '{target_term}'")
                        replacement_found = True
                        break

            # 特殊处理：单独的双下划线或术语名+下划线
            if not replacement_found:
                if re.match(r'__\s*$', matched_text) or re.match(r'__\s+', matched_text):
                    result_text = result_text.replace(matched_text, "")
                    print(f"    ✓ 删除单独双下划线: '{matched_text}'")
                    replacement_found = True
                elif re.match(r'[A-Za-z]+\s+_\s*', matched_text):
                    # 提取术语名部分，保留后面的空格
                    term_match = re.match(r'([A-Za-z]+)(\s+)_\s*', matched_text)
                    if term_match:
                        term_name = term_match.group(1)
                        space_after = term_match.group(2)
                        result_text = result_text.replace(matched_text, term_name + space_after)
                        print(f"    ✓ 清理术语下划线: '{matched_text}' -> '{term_name + space_after}'")
                        replacement_found = True

            if not replacement_found:
                result_text = result_text.replace(matched_text, "")
                print(f"    ⚠ 删除无法匹配: '{matched_text}'")

    # 第二阶段：清理格式
    print("  开始格式清理...")

    # 清理多余的空格和标点
    result_text = re.sub(r'\s+', ' ', result_text)
    result_text = re.sub(r'\s*([，。！？；：])\s*', r'\1', result_text)
    result_text = re.sub(r'。+', '。', result_text)
    result_text = result_text.strip()

    print(f"  最终结果: {result_text}")
    return result_text

def test_prompt_optimization():
    """测试提示词优化"""
    print("\n\n测试提示词优化")
    print("=" * 50)

    test_cases = [
        {
            "name": "英译中提示词",
            "source_lang": "en",
            "target_lang": "zh",
            "text": "Neck, Crown, and Body are steps in the process of crystal growth.",
            "has_placeholders": True
        },
        {
            "name": "中译英提示词",
            "source_lang": "zh",
            "target_lang": "en",
            "text": "引晶、放肩、等径都是晶体生长的过程工艺步骤",
            "has_placeholders": True
        },
        {
            "name": "基础翻译提示词",
            "source_lang": "en",
            "target_lang": "zh",
            "text": "This is a simple text without terms.",
            "has_placeholders": False
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 40)

        prompt = generate_optimized_prompt(
            test_case['text'],
            test_case['source_lang'],
            test_case['target_lang'],
            test_case['has_placeholders']
        )

        print(f"生成的提示词:")
        print(prompt)

        # 检查提示词特点
        if "不要添加任何解释" in prompt:
            print("⚠ 提示词可能过于复杂")
        elif "Keep all placeholders" in prompt and test_case['has_placeholders']:
            print("✓ 正确包含占位符保护指令")
        elif not test_case['has_placeholders'] and "placeholders" not in prompt:
            print("✓ 基础翻译提示词简洁")
        else:
            print("✓ 提示词格式正确")

def generate_optimized_prompt(text, source_lang, target_lang, has_placeholders):
    """生成优化的提示词"""
    if has_placeholders:
        # 有占位符的情况
        if source_lang == 'en' and target_lang == 'zh':
            return f"Translate the following English text to Chinese. Keep all placeholders (like __TERM_001__) unchanged:\n\n{text}\n\nChinese translation:"
        elif source_lang == 'zh' and target_lang == 'en':
            return f"Translate the following Chinese text to English. Keep all placeholders (like __TERM_001__) unchanged:\n\n{text}\n\nEnglish translation:"
        else:
            return f"Translate the following text. Keep all placeholders unchanged:\n\n{text}\n\nTranslation:"
    else:
        # 基础翻译
        if source_lang == 'en' and target_lang == 'zh':
            return f"Translate the following English text to Chinese:\n\n{text}\n\nChinese translation:"
        elif source_lang == 'zh' and target_lang == 'en':
            return f"Translate the following Chinese text to English:\n\n{text}\n\nEnglish translation:"
        else:
            return f"Translate the following text:\n\n{text}\n\nTranslation:"

if __name__ == "__main__":
    test_final_cleanup()
    test_prompt_optimization()
    print("\n测试完成！")
