#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查模块导入问题
"""

import os
import sys
import importlib

def check_module(module_name):
    """检查模块是否可以导入"""
    try:
        module = importlib.import_module(module_name)
        print(f"✓ 成功导入 {module_name}")
        return module
    except ImportError as e:
        print(f"✗ 无法导入 {module_name}: {e}")
        return None

def check_file_exists(file_path):
    """检查文件是否存在"""
    exists = os.path.exists(file_path)
    print(f"{'✓' if exists else '✗'} 文件 {file_path} {'存在' if exists else '不存在'}")
    return exists

def main():
    """主函数"""
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"sys.path: {sys.path}")
    
    print("\n检查core包:")
    check_file_exists("core")
    check_file_exists("core/__init__.py")
    check_file_exists("core\\__init__.py")
    
    print("\n检查message模块:")
    check_file_exists("core/message.py")
    check_file_exists("core\\message.py")
    
    print("\n尝试导入模块:")
    check_module("core")
    check_module("core.message")
    
    # 尝试手动添加路径并导入
    if not check_module("core.message"):
        print("\n尝试调整导入路径:")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            print(f"已添加 {current_dir} 到sys.path")
            check_module("core.message")

if __name__ == "__main__":
    main()