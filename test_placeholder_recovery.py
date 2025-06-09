#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
占位符恢复机制测试脚本
"""

import re

def test_restore_placeholders(translated_text, placeholder_map):
    """测试占位符恢复功能"""
    if not placeholder_map:
        return translated_text

    result_text = translated_text
    restored_count = 0
    
    print(f"原始翻译文本: {translated_text}")
    print(f"占位符映射: {placeholder_map}")
    print("-" * 50)
    
    for placeholder, target_term in placeholder_map.items():
        print(f"尝试恢复占位符: {placeholder} -> {target_term}")
        
        # 首先尝试精确匹配
        if placeholder in result_text:
            result_text = result_text.replace(placeholder, target_term)
            restored_count += 1
            print(f"✓ 精确匹配成功: {placeholder} -> {target_term}")
        else:
            print(f"✗ 精确匹配失败: {placeholder}")
            
            # 尝试模糊匹配
            term_number = re.search(r'(\d+)', placeholder)
            if term_number:
                num = int(term_number.group(1))
                print(f"  提取术语编号: {num}")
                
                # 尝试各种可能的格式变化
                possible_formats = [
                    f"__TERM_{num:03d}__",
                    f"__TERM_{num}__",
                    f"__ TERM _ {num:03d}__",
                    f"__ TERM _ {num} __",
                    f"__ TERM_{num:03d} __",
                    f"__ TERM_{num} __",
                    f"__ TERM _ {num:03d} ___",
                    f"__ TERM _ {num} ___",
                    f"[TERM_{num}]",
                    f"[ TERM_{num} ]",
                    f"[TERM {num}]",
                    f"[ TERM {num} ]",
                    f"TERM_{num}",
                    f"TERM {num}",
                    f"_TERM_{num}_",
                    f"_TERM {num}_"
                ]
                
                found = False
                for possible_format in possible_formats:
                    if possible_format in result_text:
                        print(f"  ✓ 模糊匹配成功: {possible_format} -> {target_term}")
                        result_text = result_text.replace(possible_format, target_term)
                        restored_count += 1
                        found = True
                        break
                    else:
                        print(f"  ✗ 尝试格式: {possible_format}")
                
                if not found:
                    print(f"  ✗ 所有格式都匹配失败")
            else:
                print(f"  ✗ 无法提取术语编号")
    
    print("-" * 50)
    print(f"恢复结果: {result_text}")
    print(f"恢复统计: 期望 {len(placeholder_map)} 个，实际恢复 {restored_count} 个")
    
    return result_text

def main():
    """主测试函数"""
    print("占位符恢复机制测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "name": "基本占位符变形测试",
            "translated_text": "At __ TERM _ 001__, the growth speed cannot be随意ly manually adjusted.",
            "placeholder_map": {"__TERM_001__": "Neck"}
        },
        {
            "name": "多占位符测试",
            "translated_text": "During the process of __ TERM_002__, attention should be paid to controlling the speed of __ TERM_001__.",
            "placeholder_map": {
                "__TERM_001__": "Neck",
                "__TERM_002__": "Crown"
            }
        },
        {
            "name": "额外下划线测试",
            "translated_text": "The __ TERM _ 001 ___ stage requires stable temperature and speed.",
            "placeholder_map": {"__TERM_001__": "Body"}
        },
        {
            "name": "方括号格式测试",
            "translated_text": "The [TERM_1] process needs careful control.",
            "placeholder_map": {"__TERM_001__": "Neck"}
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print("=" * 40)
        
        result = test_restore_placeholders(
            test_case['translated_text'],
            test_case['placeholder_map']
        )
        
        print(f"最终结果: {result}")
        print()

if __name__ == "__main__":
    main()
