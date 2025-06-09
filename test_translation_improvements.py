#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译系统改进测试脚本
测试中译英和英译中模式下的占位符处理和质量验证
"""

import re
import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_placeholder_recovery():
    """测试占位符恢复机制"""
    print("=" * 60)
    print("测试占位符恢复机制")
    print("=" * 60)

    # 模拟翻译结果中的各种占位符变形
    test_cases = [
        {
            "name": "英译中常见变形 - 括号和TERMS复数",
            "translated_text": "(引晶)、 (放肩) 和 (等径) 这些过程都是结晶生长的过程。",
            "original_placeholder_map": {
                "__TERM_001__": "放肩",
                "__TERM_002__": "等径",
                "__TERM_003__": "引晶"
            },
            "expected_result": "引晶、放肩和等径这些过程都是结晶生长的过程。"
        },
        {
            "name": "复杂变形测试",
            "translated_text": "The processes of (__ TERM 003__), (__ TERMS 001__), and (__ TERMS SLL_) are all crystallization growth procedures.",
            "original_placeholder_map": {
                "__TERM_001__": "Crown",
                "__TERM_002__": "Body",
                "__TERM_003__": "Neck"
            },
            "expected_result": "The processes of Neck, Crown, and Body are all crystallization growth procedures."
        },
        {
            "name": "混合格式测试",
            "translated_text": "在 __ TERM_001__ 阶段，需要控制 [TERM_2] 的速度和 (__ TERMS 003__) 的温度。",
            "original_placeholder_map": {
                "__TERM_001__": "引晶",
                "__TERM_002__": "等径",
                "__TERM_003__": "放肩"
            },
            "expected_result": "在引晶阶段，需要控制等径的速度和放肩的温度。"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        print(f"输入文本: {test_case['translated_text']}")
        print(f"占位符映射: {test_case['original_placeholder_map']}")

        # 模拟占位符恢复过程
        result = simulate_placeholder_recovery(
            test_case['translated_text'],
            test_case['original_placeholder_map']
        )

        print(f"恢复结果: {result}")
        print(f"期望结果: {test_case['expected_result']}")

        # 检查是否还有占位符残留
        remaining_placeholders = find_remaining_placeholders(result)
        if remaining_placeholders:
            print(f"⚠ 发现残留占位符: {remaining_placeholders}")
        else:
            print("✓ 无占位符残留")

def simulate_placeholder_recovery(translated_text, placeholder_map):
    """模拟占位符恢复过程"""
    result_text = translated_text
    restored_count = 0

    # 第一阶段：精确匹配和模糊匹配
    for placeholder, target_term in placeholder_map.items():
        # 首先尝试精确匹配
        if placeholder in result_text:
            result_text = result_text.replace(placeholder, target_term)
            restored_count += 1
            print(f"  ✓ 精确恢复: '{placeholder}' -> '{target_term}'")
        else:
            # 尝试模糊匹配
            term_number = re.search(r'(\d+)', placeholder)
            if term_number:
                num = int(term_number.group(1))
                # 各种可能的格式变化
                possible_formats = [
                    f"__TERM_{num:03d}__",
                    f"__TERM_{num}__",
                    f"__ TERM _ {num:03d}__",
                    f"__ TERM _ {num} __",
                    f"__ TERM_{num:03d} __",
                    f"__ TERM_{num} __",
                    f"(__ TERM {num:03d}__)",
                    f"(__ TERM_{num:03d}__)",
                    f"(__ TERM _ {num:03d}__)",
                    f"(__ TERM _ {num} __)",
                    f"(__ TERMS {num:03d}__)",
                    f"(__ TERMS _ {num:03d}__)",
                    f"(__ TERMS _ {num} __)",
                    f"(__ TERMS {num}__)",
                    f"__ TERMS {num:03d}__",
                    f"__ TERMS _ {num:03d}__",
                    f"__ TERMS _ {num} __",
                    f"__ TERMS {num}__",
                    f"[TERM_{num}]",
                    f"[ TERM_{num} ]",
                    f"[TERM {num}]",
                    f"[ TERM {num} ]",
                    f"TERM_{num}",
                    f"TERM {num}",
                ]

                found = False
                for possible_format in possible_formats:
                    if possible_format in result_text:
                        result_text = result_text.replace(possible_format, target_term)
                        restored_count += 1
                        print(f"  ✓ 模糊恢复: '{possible_format}' -> '{target_term}'")
                        found = True
                        break

                if not found:
                    # 使用正则表达式进行更灵活的匹配
                    patterns = [
                        rf'\(\s*__\s*TERMS?\s*_?\s*{num:03d}\s*_*__\s*\)',
                        rf'\(\s*__\s*TERMS?\s*_?\s*{num}\s*_*__\s*\)',
                        rf'\(\s*__\s*TERMS?\s*[^)]*{num}[^)]*\)',
                        rf'__\s*TERMS?\s*_?\s*{num:03d}\s*_*__',
                        rf'__\s*TERMS?\s*_?\s*{num}\s*_*__',
                        rf'\[\s*TERMS?\s*_?\s*{num:03d}\s*\]',
                        rf'\[\s*TERMS?\s*_?\s*{num}\s*\]',
                        rf'TERMS?\s*_?\s*{num:03d}',
                        rf'TERMS?\s*_?\s*{num}',
                    ]

                    for pattern in patterns:
                        matches = list(re.finditer(pattern, result_text, re.IGNORECASE))
                        for match in matches:
                            matched_text = match.group()
                            result_text = result_text.replace(matched_text, target_term)
                            restored_count += 1
                            print(f"  ✓ 正则恢复: '{matched_text}' -> '{target_term}'")
                            found = True
                            break
                        if found:
                            break

                if not found:
                    print(f"  ✗ 未找到: '{placeholder}' -> '{target_term}'")

    # 第二阶段：清理残留占位符
    cleanup_patterns = [
        r'\(\s*__+\s*TERMS?\s*[^)]*\d+[^)]*__*\s*\)',
        r'__+\s*TERMS?\s*_?\s*\d+\s*_*__+',
        r'\[\s*TERMS?\s*_?\s*\d+\s*\]',
        r'TERMS?\s*_?\s*\d+',
        r'\(\s*[^)]*TERMS?[^)]*\d+[^)]*\)',
    ]

    cleaned_count = 0
    for pattern in cleanup_patterns:
        matches = list(re.finditer(pattern, result_text, re.IGNORECASE))
        for match in matches:
            matched_text = match.group()
            print(f"  ⚠ 发现残留: '{matched_text}'")

            # 尝试从匹配的文本中提取数字，找到对应的术语
            num_match = re.search(r'(\d+)', matched_text)
            if num_match:
                num = int(num_match.group(1))
                # 查找对应的术语
                for placeholder, target_term in placeholder_map.items():
                    if f"{num:03d}" in placeholder or str(num) in placeholder:
                        result_text = result_text.replace(matched_text, target_term)
                        print(f"  ✓ 清理恢复: '{matched_text}' -> '{target_term}'")
                        cleaned_count += 1
                        break
                else:
                    # 找不到对应术语，删除占位符
                    result_text = result_text.replace(matched_text, "")
                    print(f"  ⚠ 删除异常: '{matched_text}'")
                    cleaned_count += 1
            else:
                # 无法提取数字，删除
                result_text = result_text.replace(matched_text, "")
                print(f"  ⚠ 删除无效: '{matched_text}'")
                cleaned_count += 1

    # 清理多余的空格和标点
    result_text = re.sub(r'\s+', ' ', result_text)
    result_text = re.sub(r'\s*([，。！？；：])\s*', r'\1', result_text)
    result_text = re.sub(r'\(\s*\)', '', result_text)

    # 清理术语周围的多余括号（如果术语被单独括起来）
    bracket_cleaned = 0
    for placeholder, target_term in placeholder_map.items():
        # 清理术语周围的括号
        patterns_to_clean = [
            rf'\(\s*{re.escape(target_term)}\s*\)([，、。！？；：\s])',  # (术语)后跟标点
            rf'\(\s*{re.escape(target_term)}\s*\)$',  # 行末的(术语)
            rf'^\(\s*{re.escape(target_term)}\s*\)',  # 行首的(术语)
            rf'\(\s*{re.escape(target_term)}\s*\)\s+',  # (术语)后跟空格
        ]

        for pattern in patterns_to_clean:
            # 替换时保留后面的标点或空格
            if re.search(pattern, result_text):
                result_text = re.sub(pattern, lambda m: target_term + (m.group(1) if len(m.groups()) > 0 else ''), result_text)
                print(f"  ✓ 清理术语括号: '({target_term})' -> '{target_term}'")
                bracket_cleaned += 1
                break

    result_text = result_text.strip()

    print(f"  统计: 正常恢复 {restored_count}/{len(placeholder_map)}, 清理残留 {cleaned_count}, 清理括号 {bracket_cleaned}")
    return result_text

def find_remaining_placeholders(text):
    """查找文本中剩余的占位符"""
    patterns = [
        r'__[^_]*\d+[^_]*__',
        r'\[[^\]]*\d+[^\]]*\]',
        r'\([^)]*TERM[^)]*\d+[^)]*\)',
        r'TERM\s*\d+',
        r'_+[A-Za-z]*\d+_*'
    ]

    remaining = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if re.search(r'(TERM|Term|\d{3}|__\d+__|_\d+_)', match, re.IGNORECASE):
                remaining.append(match)

    return list(set(remaining))

def test_translation_quality_validation():
    """测试翻译质量验证"""
    print("\n" + "=" * 60)
    print("测试翻译质量验证")
    print("=" * 60)

    test_cases = [
        {
            "name": "英译中长度检查",
            "original": "The processes of Neck, Crown, and Body are all crystallization growth procedures.",
            "translated": "引晶、放肩和等径的过程都是结晶生长工序。",
            "source_lang": "en",
            "target_lang": "zh",
            "should_pass": True
        },
        {
            "name": "中译英长度检查",
            "original": "引晶、放肩、等径都是晶体生长的过程工艺",
            "translated": "Neck, Crown, and Body are all crystal growth process technologies.",
            "source_lang": "zh",
            "target_lang": "en",
            "should_pass": True
        },
        {
            "name": "翻译过短测试",
            "original": "这是一个很长的句子，包含了很多重要的技术信息和专业术语，需要准确翻译。",
            "translated": "Short.",
            "source_lang": "zh",
            "target_lang": "en",
            "should_pass": False
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        print(f"原文: {test_case['original']}")
        print(f"译文: {test_case['translated']}")
        print(f"翻译方向: {test_case['source_lang']} -> {test_case['target_lang']}")

        issues = simulate_quality_validation(
            test_case['original'],
            test_case['translated'],
            test_case['source_lang'],
            test_case['target_lang']
        )

        if issues:
            print(f"发现问题: {issues}")
            if test_case['should_pass']:
                print("❌ 测试失败：不应该有问题")
            else:
                print("✓ 测试通过：正确检测到问题")
        else:
            print("无问题")
            if test_case['should_pass']:
                print("✓ 测试通过：翻译质量良好")
            else:
                print("❌ 测试失败：应该检测到问题")

def simulate_quality_validation(original_text, translated_text, source_lang, target_lang):
    """模拟翻译质量验证"""
    issues = []

    # 规范化语言代码
    def normalize_language_code(lang_code, text_sample=""):
        if lang_code == 'auto':
            if re.search(r'[\u4e00-\u9fff]', text_sample):
                return 'zh'
            elif re.search(r'^[a-zA-Z\s\.,!?;:\'"-]+$', text_sample.strip()):
                return 'en'
            else:
                return 'zh'
        return lang_code

    normalized_source_lang = normalize_language_code(source_lang, original_text)
    normalized_target_lang = normalize_language_code(target_lang, translated_text)

    # 检查翻译是否为空或过短
    if not translated_text.strip():
        issues.append("翻译结果为空")
    else:
        original_len = len(original_text.strip())
        translated_len = len(translated_text.strip())

        if normalized_source_lang == 'en' and normalized_target_lang == 'zh':
            min_ratio = 0.2  # 中文可以比英文短很多
        elif normalized_source_lang == 'zh' and normalized_target_lang == 'en':
            min_ratio = 0.8  # 英文不应该比中文短太多
        else:
            min_ratio = 0.3

        if translated_len < original_len * min_ratio:
            if original_len > 20:
                issues.append("翻译结果过短，可能不完整")

    return issues

if __name__ == "__main__":
    print("翻译系统改进测试")
    test_placeholder_recovery()
    test_translation_quality_validation()
    print("\n测试完成！")
