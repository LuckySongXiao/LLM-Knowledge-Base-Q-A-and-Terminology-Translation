#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语库升级脚本
将现有术语库升级为支持多术语的格式
"""

import json
import os
import shutil
from datetime import datetime

def backup_original_terms():
    """备份原始术语库"""
    original_path = "data/terms/terms.json"
    backup_path = f"data/terms/terms_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    if os.path.exists(original_path):
        shutil.copy2(original_path, backup_path)
        print(f"✓ 原始术语库已备份到: {backup_path}")
        return True
    else:
        print(f"✗ 原始术语库不存在: {original_path}")
        return False

def load_terms(file_path):
    """加载术语库"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            terms = json.load(f)
        print(f"✓ 成功加载术语库: {file_path}")
        print(f"  术语数量: {len(terms)}")
        return terms
    except Exception as e:
        print(f"✗ 加载术语库失败: {e}")
        return None

def upgrade_term_entry(chinese_term, term_data):
    """升级单个术语条目"""
    if not isinstance(term_data, dict):
        # 简单字符串格式，转换为字典格式
        return {
            "source_term": chinese_term,
            "target_term": str(term_data),
            "definition": str(term_data),
            "metadata": {
                "source_lang": "zh",
                "target_lang": "en",
                "type": "term",
                "upgraded_time": datetime.now().isoformat(),
                "priority_note": f"{str(term_data).split(',')[0] if ',' in str(term_data) else str(term_data)}享有最高翻译权限"
            }
        }
    
    # 已经是字典格式，检查是否需要升级
    target_term = term_data.get('target_term', term_data.get('definition', ''))
    
    # 更新metadata
    metadata = term_data.get('metadata', {})
    if 'priority_note' not in metadata:
        # 添加优先级说明
        first_term = target_term.split(',')[0].strip() if ',' in target_term else target_term
        metadata['priority_note'] = f"{first_term}享有最高翻译权限"
        metadata['upgraded_time'] = datetime.now().isoformat()
    
    # 确保必要字段存在
    upgraded_entry = {
        "source_term": term_data.get('source_term', chinese_term),
        "target_term": target_term,
        "definition": term_data.get('definition', target_term),
        "vector_id": term_data.get('vector_id', ''),
        "metadata": metadata
    }
    
    return upgraded_entry

def upgrade_terms_database(input_path, output_path):
    """升级术语库"""
    print("=" * 60)
    print("开始升级术语库")
    print("=" * 60)
    
    # 加载原始术语库
    original_terms = load_terms(input_path)
    if not original_terms:
        return False
    
    # 升级术语库
    upgraded_terms = {}
    upgrade_count = 0
    
    for chinese_term, term_data in original_terms.items():
        print(f"升级术语: {chinese_term}")
        
        # 升级术语条目
        upgraded_entry = upgrade_term_entry(chinese_term, term_data)
        upgraded_terms[chinese_term] = upgraded_entry
        
        # 显示升级信息
        target_term = upgraded_entry['target_term']
        if ',' in target_term:
            terms_list = [term.strip() for term in target_term.split(',')]
            print(f"  主要术语: {terms_list[0]}")
            print(f"  备用术语: {terms_list[1:]}")
        else:
            print(f"  术语: {target_term}")
        
        upgrade_count += 1
        print("-" * 40)
    
    # 保存升级后的术语库
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(upgraded_terms, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 升级完成！")
        print(f"  升级术语数量: {upgrade_count}")
        print(f"  输出文件: {output_path}")
        return True
        
    except Exception as e:
        print(f"✗ 保存升级后术语库失败: {e}")
        return False

def validate_upgraded_terms(file_path):
    """验证升级后的术语库"""
    print("\n" + "=" * 60)
    print("验证升级后的术语库")
    print("=" * 60)
    
    terms = load_terms(file_path)
    if not terms:
        return False
    
    validation_results = {
        'total_terms': len(terms),
        'multi_term_entries': 0,
        'single_term_entries': 0,
        'missing_metadata': 0,
        'missing_priority_note': 0
    }
    
    for chinese_term, term_data in terms.items():
        target_term = term_data.get('target_term', '')
        metadata = term_data.get('metadata', {})
        
        # 检查是否为多术语条目
        if ',' in target_term:
            validation_results['multi_term_entries'] += 1
            terms_list = [term.strip() for term in target_term.split(',')]
            print(f"多术语条目: {chinese_term}")
            print(f"  主要术语: {terms_list[0]}")
            print(f"  备用术语: {terms_list[1:]}")
        else:
            validation_results['single_term_entries'] += 1
        
        # 检查metadata
        if not metadata:
            validation_results['missing_metadata'] += 1
        elif 'priority_note' not in metadata:
            validation_results['missing_priority_note'] += 1
    
    print(f"\n验证结果:")
    print(f"  总术语数: {validation_results['total_terms']}")
    print(f"  多术语条目: {validation_results['multi_term_entries']}")
    print(f"  单术语条目: {validation_results['single_term_entries']}")
    print(f"  缺少metadata: {validation_results['missing_metadata']}")
    print(f"  缺少优先级说明: {validation_results['missing_priority_note']}")
    
    return validation_results

def main():
    """主函数"""
    print("术语库升级工具")
    print("=" * 60)
    
    # 文件路径
    original_path = "data/terms/terms.json"
    upgraded_path = "data/terms/terms_upgraded.json"
    
    # 1. 备份原始术语库
    if not backup_original_terms():
        return
    
    # 2. 升级术语库
    if not upgrade_terms_database(original_path, upgraded_path):
        return
    
    # 3. 验证升级结果
    validation_results = validate_upgraded_terms(upgraded_path)
    
    # 4. 询问是否替换原始文件
    print(f"\n{'='*60}")
    print("升级完成！")
    print(f"升级后的术语库保存在: {upgraded_path}")
    print(f"原始术语库已备份")
    
    replace = input("\n是否用升级后的术语库替换原始文件？(y/N): ").strip().lower()
    if replace == 'y':
        try:
            shutil.copy2(upgraded_path, original_path)
            print(f"✓ 已替换原始术语库文件")
        except Exception as e:
            print(f"✗ 替换失败: {e}")
    else:
        print("保持原始文件不变")
    
    print(f"\n{'='*60}")
    print("术语库升级完成！")
    print("主要改进:")
    print("1. ✓ 支持多个外语术语（用逗号分隔）")
    print("2. ✓ 添加术语优先级说明")
    print("3. ✓ 完善metadata信息")
    print("4. ✓ 保持向后兼容性")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
