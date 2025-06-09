"""
模型加载和推理测试脚本
用于测试模型加载和基本文本生成功能
"""

import os
import torch
from core.base_engine import BaseEngine
from core.model_quantizer import ModelQuantizer, QuantizationLevel

def test_model_loading():
    """测试模型加载和推理功能"""
    print("===== 模型加载和推理测试 =====")
    
    # 打印系统信息
    print(f"Python版本: {sys.version}")
    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA是否可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA版本: {torch.version.cuda}")
        print(f"GPU设备: {torch.cuda.get_device_name(0)}")
        print(f"显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    
    # 查找可用的模型
    print("\n查找可用模型...")
    model_dir = "QWEN"
    model_path = None
    
    if os.path.exists(model_dir) and os.path.isdir(model_dir):
        subdirs = [d for d in os.listdir(model_dir) if os.path.isdir(os.path.join(model_dir, d))]
        if subdirs:
            model_path = os.path.join(model_dir, subdirs[0])
            print(f"找到模型: {model_path}")
    
    if not model_path:
        print("未找到可用的模型，请检查模型目录")
        return
    
    # 初始化量化管理器
    print("\n初始化量化管理器...")
    settings = {'model_path': model_path}
    quantizer = ModelQuantizer(settings)
    print(f"自动选择的量化级别: {quantizer.auto_level.name}")
    
    # 创建引擎并加载模型
    print("\n创建引擎并加载模型...")
    engine = BaseEngine(settings)
    success = engine.load_models()
    
    if not success:
        print("模型加载失败!")
        return
    
    # 打印模型类型信息
    print("\n模型信息:")
    print(f"模型类型: {type(engine.model)}")
    if isinstance(engine.model, dict):
        print("模型是字典类型，包含以下键:")
        for key in engine.model.keys():
            print(f"  - {key}")
    
    # 尝试生成文本
    print("\n尝试生成文本...")
    prompt = "你好，请介绍一下自己"
    
    messages = [{"role": "user", "content": prompt}]
    prepared_prompt = engine._prepare_prompt(messages)
    
    print(f"输入提示: {prompt}")
    print(f"处理后的提示: {prepared_prompt[:100]}...")
    
    try:
        # 设置生成参数
        generation_config = {
            "max_new_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True
        }
        
        # 使用transformers方法生成
        response = engine._generate_with_transformers(prepared_prompt, generation_config)
        print("\n生成的回复:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        print("\n测试完成!")
    except Exception as e:
        import traceback
        print(f"生成文本时出错: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    test_model_loading() 