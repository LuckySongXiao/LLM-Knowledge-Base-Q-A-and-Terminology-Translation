"""向量工具模块"""

import os
import sys
import numpy as np

def load_vector_model(model_path):
    """加载向量模型"""
    try:
        print(f"尝试加载向量模型: {model_path}")
        
        # 检查模型路径是否存在
        if not os.path.exists(model_path):
            print(f"模型路径不存在: {model_path}")
            return None
        
        # 尝试导入sentence_transformers
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("未安装sentence_transformers库，尝试安装...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence_transformers"])
            from sentence_transformers import SentenceTransformer
        
        # 加载模型
        print(f"使用SentenceTransformer加载模型: {model_path}")
        model = SentenceTransformer(model_path)
        print("模型加载成功")
        
        return model
    
    except Exception as e:
        print(f"加载向量模型失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_embedding(model, text):
    """获取文本的向量嵌入"""
    try:
        if not model:
            print("错误: 模型未加载")
            return None
        
        # 使用模型生成向量
        vector = model.encode([text])[0]
        
        # 返回numpy数组
        return np.array(vector)
    
    except Exception as e:
        print(f"生成向量嵌入失败: {e}")
        import traceback
        traceback.print_exc()
        return None 