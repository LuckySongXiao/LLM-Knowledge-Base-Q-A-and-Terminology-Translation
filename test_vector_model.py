#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试BGE-M3向量模型加载和向量生成
"""

import os
import sys
import time
import numpy as np
import json

# 检查基本路径
def check_paths():
    """检查BGE-M3相关路径"""
    print("===== 开始检查模型路径 =====")
    
    # 当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"当前目录: {current_dir}")
    
    # 可能的模型路径
    possible_paths = [
        os.path.join(current_dir, "BAAI", "bge-m3"),
        os.path.join(current_dir, "BAAI", "models", "BAAI", "bge-m3"),
        os.path.join("D:", "AI_project", "vllm_模型应用", "BAAI", "bge-m3")
    ]
    
    # 检查每个路径
    for path in possible_paths:
        print(f"\n检查路径: {path}")
        if os.path.exists(path):
            print(f"  ✓ 路径存在")
            # 检查关键文件
            required_files = ["modules.json", "tokenizer.json", "config.json", "pytorch_model.bin"]
            missing_files = []
            for file in required_files:
                file_path = os.path.join(path, file)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    print(f"  ✓ {file} 存在 ({file_size:.2f}MB)")
                else:
                    missing_files.append(file)
                    print(f"  ✗ {file} 不存在")
            
            if not missing_files:
                print("\n✓ 发现完整的BGE-M3模型")
                return path
            else:
                print(f"\n✗ 此路径存在但缺少必要文件: {', '.join(missing_files)}")
        else:
            print(f"  ✗ 路径不存在")
    
    print("\n❌ 未找到完整的BGE-M3模型路径")
    return None

# 尝试加载模型
def test_model_loading(model_path=None):
    """测试加载BGE-M3模型的不同方法"""
    if not model_path:
        model_path = check_paths()
        if not model_path:
            print("无法继续，未找到有效的模型路径")
            return False
    
    print("\n===== 开始测试模型加载 =====")
    
    # 方法1: 使用sentence-transformers
    print("\n方法1: 使用sentence-transformers加载")
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        print(f"CUDA是否可用: {torch.cuda.is_available()}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"将使用设备: {device}")
        
        from sentence_transformers import SentenceTransformer
        print(f"开始加载模型: {model_path}")
        start_time = time.time()
        model = SentenceTransformer(model_path, device=device)
        load_time = time.time() - start_time
        print(f"✓ 模型加载成功! 耗时: {load_time:.2f}秒")
        
        # 测试编码
        test_text = "这是一个测试句子，用来检查模型是否能够正确生成向量。"
        print(f"测试编码文本: '{test_text}'")
        
        start_time = time.time()
        embedding = model.encode(test_text)
        encode_time = time.time() - start_time
        
        print(f"✓ 编码成功! 耗时: {encode_time:.2f}秒")
        print(f"向量维度: {embedding.shape if hasattr(embedding, 'shape') else len(embedding)}")
        print(f"向量前5个元素: {embedding[:5]}")
        
        return model
    
    except Exception as e:
        import traceback
        print(f"❌ 模型加载失败: {e}")
        traceback.print_exc()
        
        # 方法2: 尝试使用FlagEmbedding
        print("\n方法2: 尝试使用FlagEmbedding加载")
        try:
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError:
                print("FlagEmbedding未安装，尝试安装...")
                import subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", "FlagEmbedding>=1.2.0"], check=True)
                from FlagEmbedding import BGEM3FlagModel
            
            print(f"开始加载模型: {model_path}")
            start_time = time.time()
            model = BGEM3FlagModel(model_path, device=device)
            load_time = time.time() - start_time
            print(f"✓ 模型加载成功! 耗时: {load_time:.2f}秒")
            
            # 测试编码
            test_text = "这是一个测试句子，用来检查模型是否能够正确生成向量。"
            print(f"测试编码文本: '{test_text}'")
            
            start_time = time.time()
            embedding = model.encode(test_text)
            encode_time = time.time() - start_time
            
            print(f"✓ 编码成功! 耗时: {encode_time:.2f}秒")
            if isinstance(embedding, dict):
                print(f"返回类型: dict，键: {list(embedding.keys())}")
                if 'dense' in embedding:
                    dense_embedding = embedding['dense']
                    print(f"Dense向量维度: {dense_embedding.shape if hasattr(dense_embedding, 'shape') else len(dense_embedding)}")
                    print(f"Dense向量前5个元素: {dense_embedding[:5]}")
            else:
                print(f"向量维度: {embedding.shape if hasattr(embedding, 'shape') else len(embedding)}")
                print(f"向量前5个元素: {embedding[:5]}")
            
            return model
            
        except Exception as e2:
            print(f"❌ FlagEmbedding加载也失败: {e2}")
            import traceback
            traceback.print_exc()
            return None

# 测试向量数据库
def test_vector_db(model=None):
    """测试向量数据库功能"""
    print("\n===== 测试向量数据库 =====")
    
    # 导入向量数据库类
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from core.vector_db import VectorDB
        from config.settings import Settings
        
        # 初始化设置和向量数据库
        print("初始化向量数据库...")
        settings = Settings()
        vector_db = VectorDB(settings)
        
        # 如果已有模型，直接设置
        if model:
            print("使用已加载的模型")
            model_path = check_paths()
            vector_db.set_model({
                "name": "bge-m3",
                "path": model_path,
                "model": model
            })
        else:
            # 否则调用加载
            model_path = check_paths()
            print(f"尝试加载模型: {model_path}")
            model_info = {
                "name": "bge-m3",
                "path": model_path
            }
            success = vector_db.set_model(model_info)
            if not success:
                print("❌ 向量数据库模型加载失败")
                return False
        
        # 测试编码
        test_text = "向量数据库测试文本"
        print(f"测试向量编码: '{test_text}'")
        vector = vector_db.encode_text(test_text)
        
        if vector is not None:
            print(f"✓ 向量编码成功，维度: {vector.shape if hasattr(vector, 'shape') else len(vector)}")
            
            # 测试添加向量
            print("测试添加向量到数据库...")
            vector_id = vector_db.add(test_text, vector)
            if vector_id:
                print(f"✓ 添加成功，ID: {vector_id}")
                
                # 测试搜索
                print("测试向量搜索...")
                results = vector_db.search(test_text, top_k=15)
                if results:
                    print(f"✓ 搜索成功，找到 {len(results)} 条结果")
                    for i, result in enumerate(results[:3], 1):
                        if isinstance(result, dict):
                            print(f"  结果 {i}: 相似度 {result.get('similarity', 'N/A')}")
                        else:
                            print(f"  结果 {i}: {result}")
                else:
                    print("❌ 搜索无结果")
                
                return True
            else:
                print("❌ 添加向量失败")
                return False
        else:
            print("❌ 向量编码失败")
            return False
    
    except Exception as e:
        print(f"❌ 向量数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("===== BGE-M3向量模型测试工具 =====")
    # 第一步：检查路径
    model_path = check_paths()
    
    # 第二步：测试模型加载
    model = test_model_loading(model_path)
    
    # 第三步：测试向量数据库
    if model:
        test_vector_db(model)
    else:
        test_vector_db()
    
    print("\n测试完成!") 