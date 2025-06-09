#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据路径诊断工具
用于检查知识库和术语库文件的路径和访问权限问题
"""

import os
import json
import sys
from pathlib import Path

def check_file_access(file_path):
    """检查文件访问权限"""
    try:
        # 检查文件是否存在
        exists = os.path.exists(file_path)
        
        # 检查是否为文件
        is_file = os.path.isfile(file_path) if exists else False
        
        # 检查读取权限
        readable = os.access(file_path, os.R_OK) if exists else False
        
        # 检查写入权限
        writable = os.access(file_path, os.W_OK) if exists else False
        
        # 获取文件大小
        size = os.path.getsize(file_path) if exists and is_file else 0
        
        return {
            'exists': exists,
            'is_file': is_file,
            'readable': readable,
            'writable': writable,
            'size': size,
            'absolute_path': os.path.abspath(file_path)
        }
    except Exception as e:
        return {
            'exists': False,
            'error': str(e),
            'absolute_path': os.path.abspath(file_path)
        }

def check_directory_access(dir_path):
    """检查目录访问权限"""
    try:
        # 检查目录是否存在
        exists = os.path.exists(dir_path)
        
        # 检查是否为目录
        is_dir = os.path.isdir(dir_path) if exists else False
        
        # 检查读取权限
        readable = os.access(dir_path, os.R_OK) if exists else False
        
        # 检查写入权限
        writable = os.access(dir_path, os.W_OK) if exists else False
        
        # 列出目录内容
        contents = []
        if exists and is_dir and readable:
            try:
                contents = os.listdir(dir_path)
            except Exception as e:
                contents = [f"Error listing: {e}"]
        
        return {
            'exists': exists,
            'is_dir': is_dir,
            'readable': readable,
            'writable': writable,
            'contents': contents,
            'absolute_path': os.path.abspath(dir_path)
        }
    except Exception as e:
        return {
            'exists': False,
            'error': str(e),
            'absolute_path': os.path.abspath(dir_path)
        }

def test_json_loading(file_path):
    """测试JSON文件加载"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'success': True,
            'type': type(data).__name__,
            'size': len(data) if isinstance(data, (dict, list)) else 'N/A',
            'keys': list(data.keys())[:10] if isinstance(data, dict) else 'N/A'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    """主诊断函数"""
    print("=" * 60)
    print("数据路径诊断工具")
    print("=" * 60)
    
    # 当前工作目录
    print(f"\n当前工作目录: {os.getcwd()}")
    print(f"脚本所在目录: {os.path.dirname(os.path.abspath(__file__))}")
    
    # 检查数据目录结构
    data_paths = [
        'data',
        'data/knowledge',
        'data/terms', 
        'data/vectors',
        'data/term_vectors'
    ]
    
    print("\n" + "=" * 40)
    print("检查数据目录结构")
    print("=" * 40)
    
    for path in data_paths:
        print(f"\n检查目录: {path}")
        result = check_directory_access(path)
        
        print(f"  存在: {result['exists']}")
        print(f"  是目录: {result.get('is_dir', 'N/A')}")
        print(f"  可读: {result.get('readable', 'N/A')}")
        print(f"  可写: {result.get('writable', 'N/A')}")
        print(f"  绝对路径: {result['absolute_path']}")
        
        if result.get('contents'):
            print(f"  内容: {result['contents']}")
        
        if 'error' in result:
            print(f"  错误: {result['error']}")
    
    # 检查关键数据文件
    data_files = [
        'data/knowledge/items.json',
        'data/terms/terms.json',
        'data/vectors/vectors.json',
        'data/term_vectors/vectors.json'
    ]
    
    print("\n" + "=" * 40)
    print("检查关键数据文件")
    print("=" * 40)
    
    for file_path in data_files:
        print(f"\n检查文件: {file_path}")
        result = check_file_access(file_path)
        
        print(f"  存在: {result['exists']}")
        print(f"  是文件: {result.get('is_file', 'N/A')}")
        print(f"  可读: {result.get('readable', 'N/A')}")
        print(f"  可写: {result.get('writable', 'N/A')}")
        print(f"  大小: {result.get('size', 'N/A')} 字节")
        print(f"  绝对路径: {result['absolute_path']}")
        
        if 'error' in result:
            print(f"  错误: {result['error']}")
        
        # 如果文件存在且可读，测试JSON加载
        if result.get('exists') and result.get('readable'):
            print("  测试JSON加载:")
            json_result = test_json_loading(file_path)
            if json_result['success']:
                print(f"    成功: 类型={json_result['type']}, 大小={json_result['size']}")
                if json_result['keys'] != 'N/A':
                    print(f"    键示例: {json_result['keys']}")
            else:
                print(f"    失败: {json_result['error']}")
    
    # 测试不同路径格式
    print("\n" + "=" * 40)
    print("测试不同路径格式")
    print("=" * 40)
    
    test_paths = [
        'data/terms/terms.json',           # 正斜杠
        'data\\terms\\terms.json',         # 反斜杠
        os.path.join('data', 'terms', 'terms.json'),  # os.path.join
        Path('data') / 'terms' / 'terms.json'         # pathlib
    ]
    
    for i, path in enumerate(test_paths):
        path_str = str(path)
        print(f"\n路径格式 {i+1}: {path_str}")
        exists = os.path.exists(path_str)
        print(f"  存在: {exists}")
        if exists:
            print(f"  绝对路径: {os.path.abspath(path_str)}")
    
    # 检查Python路径和模块导入
    print("\n" + "=" * 40)
    print("检查Python环境")
    print("=" * 40)
    
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.path[:3]}...")  # 只显示前3个路径
    
    # 尝试导入相关模块
    modules_to_test = ['json', 'os', 'pathlib']
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"模块 {module}: 可用")
        except ImportError as e:
            print(f"模块 {module}: 不可用 - {e}")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
