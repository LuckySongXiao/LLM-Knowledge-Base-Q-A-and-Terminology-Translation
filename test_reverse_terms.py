#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向术语库测试脚本
"""

import json

def create_reverse_term_cache(terms, source_lang, target_lang):
    """创建反向术语库缓存（用于外语→中文翻译）

    术语库结构：
    - 键（key）：中文术语
    - 值（value）：外语术语

    反向翻译时：
    - 匹配：外语术语（原术语库的值）
    - 替换：中文术语（原术语库的键）
    """
    reverse_terms = {}

    if not terms:
        return reverse_terms

    print(f"创建反向术语库缓存: {source_lang} → {target_lang}")

    for chinese_term, term_data in terms.items():  # chinese_term是键（中文）
        if isinstance(term_data, dict):
            metadata = term_data.get('metadata', {})
            # 检查原始术语的语言方向
            original_source_lang = metadata.get('source_lang', 'zh')  # 原始：中文
            original_target_lang = metadata.get('target_lang', 'en')  # 原始：外语

            # 如果当前翻译是外语→中文，且原术语库是中文→外语
            if (source_lang == original_target_lang and target_lang == original_source_lang):
                foreign_term = term_data.get('target_term', term_data.get('definition', ''))  # 外语术语（原值）
                if foreign_term:
                    # 创建反向映射：外语术语（小写作为查找键） → 中文术语
                    reverse_terms[foreign_term.lower()] = {
                        'source_term': foreign_term,      # 在文本中匹配的外语术语
                        'target_term': chinese_term,      # 要替换成的中文术语
                        'definition': chinese_term,
                        'metadata': {
                            'source_lang': source_lang,           # 当前翻译：外语
                            'target_lang': target_lang,           # 当前翻译：中文
                            'original_source_lang': original_source_lang,  # 原始：中文
                            'original_target_lang': original_target_lang   # 原始：外语
                        }
                    }
                    print(f"反向术语映射: '{foreign_term}' → '{chinese_term}'")

    print(f"反向术语库缓存创建完成，共 {len(reverse_terms)} 个术语")
    return reverse_terms

def test_reverse_matching(source_text, reverse_terms):
    """测试反向术语匹配"""
    matched_terms = []
    source_text_lower = source_text.lower()

    print(f"\n测试文本: {source_text}")
    print(f"小写文本: {source_text_lower}")
    print("-" * 40)

    for foreign_term_lower, term_data in reverse_terms.items():
        print(f"检查外语术语: '{foreign_term_lower}' (原始: '{term_data['source_term']}')")

        # 检查外语术语是否在文本中（不区分大小写）
        if foreign_term_lower in source_text_lower:
            foreign_term = term_data['source_term']  # 外语术语（原始大小写）
            chinese_term = term_data['target_term']  # 中文术语
            position = source_text_lower.find(foreign_term_lower)

            matched_terms.append({
                'source': foreign_term,   # 在文本中匹配到的外语术语
                'target': chinese_term,   # 要替换成的中文术语
                'position': position,
                'length': len(foreign_term)
            })
            print(f"  ✓ 找到匹配: '{foreign_term}' → '{chinese_term}'")
        else:
            # 尝试更灵活的匹配（处理单词边界）
            import re
            pattern = r'\b' + re.escape(foreign_term_lower) + r'\b'
            match = re.search(pattern, source_text_lower)
            if match:
                foreign_term = term_data['source_term']
                chinese_term = term_data['target_term']
                position = match.start()

                matched_terms.append({
                    'source': foreign_term,
                    'target': chinese_term,
                    'position': position,
                    'length': len(foreign_term)
                })
                print(f"  ✓ 找到匹配（单词边界）: '{foreign_term}' → '{chinese_term}'")
            else:
                print(f"  ✗ 未找到匹配")

    return matched_terms

def main():
    """主测试函数"""
    print("反向术语库测试")
    print("=" * 50)

    # 加载术语库
    try:
        with open('data/terms/terms.json', 'r', encoding='utf-8') as f:
            terms = json.load(f)
        print(f"加载术语库成功，共 {len(terms)} 个术语")
    except Exception as e:
        print(f"加载术语库失败: {e}")
        return

    # 创建反向术语库
    reverse_terms = create_reverse_term_cache(terms, 'en', 'zh')

    print(f"\n反向术语库内容:")
    for reverse_term, term_data in reverse_terms.items():
        print(f"  {reverse_term} → {term_data['target_term']}")

    # 测试用例
    test_cases = [
        "The neck growth speed should be carefully controlled",
        "During the body stage, maintain stable temperature",
        "The crown process requires attention to neck speed",
        "Monocrystal growth involves neck, body, and crown stages",
        "The diameter measurement during polycrystal formation"
    ]

    # 执行测试
    for test_text in test_cases:
        matched_terms = test_reverse_matching(test_text, reverse_terms)
        print(f"匹配结果: {len(matched_terms)} 个术语")
        for term in matched_terms:
            print(f"  - {term['source']} → {term['target']}")
        print()

if __name__ == "__main__":
    main()
