import re

# 测试占位符恢复
translated_text = "At __ TERM _ 001__, the growth speed cannot be随意ly manually adjusted."
placeholder_map = {"__TERM_001__": "Neck"}

print(f"原始文本: {translated_text}")
print(f"占位符映射: {placeholder_map}")

result_text = translated_text
for placeholder, target_term in placeholder_map.items():
    print(f"\n尝试恢复: {placeholder} -> {target_term}")
    
    if placeholder in result_text:
        print("✓ 精确匹配成功")
        result_text = result_text.replace(placeholder, target_term)
    else:
        print("✗ 精确匹配失败，尝试模糊匹配...")
        
        term_number = re.search(r'(\d+)', placeholder)
        if term_number:
            num = int(term_number.group(1))
            print(f"提取编号: {num}")
            
            possible_formats = [
                f"__ TERM _ {num:03d}__",
                f"__ TERM _ {num} __",
                f"__ TERM_{num:03d} __",
                f"__ TERM_{num} __"
            ]
            
            for fmt in possible_formats:
                print(f"尝试格式: '{fmt}'")
                if fmt in result_text:
                    print(f"✓ 找到匹配: '{fmt}'")
                    result_text = result_text.replace(fmt, target_term)
                    break
            else:
                print("✗ 所有格式都不匹配")

print(f"\n最终结果: {result_text}")
