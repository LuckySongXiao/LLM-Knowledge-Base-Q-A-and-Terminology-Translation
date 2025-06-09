#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检测CUDA环境和PyTorch配置的工具脚本
"""

import os
import sys
import platform
import subprocess
import importlib.util

def print_header(title):
    """打印带格式的标题"""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)

def print_section(title):
    """打印带格式的节标题"""
    print("\n" + "-" * 60)
    print(f" {title} ".center(60, "-"))
    print("-" * 60)

def check_python():
    """检查Python环境"""
    print_section("Python环境")
    print(f"Python版本: {platform.python_version()}")
    print(f"Python路径: {sys.executable}")
    print(f"系统平台: {platform.platform()}")
    print(f"处理器: {platform.processor()}")

def check_pip_packages():
    """检查关键pip包"""
    print_section("关键依赖包")
    packages = [
        "torch", "torchvision", "torchaudio", 
        "transformers", "sentence_transformers", 
        "FlagEmbedding", "PySide6", "modelscope"
    ]
    
    for package in packages:
        spec = importlib.util.find_spec(package)
        if spec is not None:
            try:
                module = importlib.import_module(package)
                if hasattr(module, "__version__"):
                    print(f"{package}: 已安装 (版本 {module.__version__})")
                else:
                    print(f"{package}: 已安装 (版本未知)")
            except ImportError:
                print(f"{package}: 已安装但无法导入")
        else:
            print(f"{package}: 未安装")

def check_cuda():
    """检查CUDA环境"""
    print_section("CUDA环境")
    
    # 检查NVIDIA驱动
    try:
        nvidia_smi = subprocess.check_output("nvidia-smi", shell=True, stderr=subprocess.STDOUT).decode('utf-8', 'ignore')
        print("NVIDIA驱动已安装")
        
        # 提取驱动版本
        for line in nvidia_smi.split('\n'):
            if "Driver Version" in line:
                print(f"驱动版本: {line.split('Driver Version:')[1].strip().split()[0]}")
            
            if "CUDA Version" in line:
                print(f"CUDA版本: {line.split('CUDA Version:')[1].strip()}")
        
        # 检查可用GPU
        if "GeForce" in nvidia_smi or "Quadro" in nvidia_smi or "Tesla" in nvidia_smi:
            print("\nGPU信息:")
            gpu_lines = []
            for i, line in enumerate(nvidia_smi.split('\n')):
                if "%" in line and "MiB" in line:
                    gpu_lines.append(line)
                    next_line = nvidia_smi.split('\n')[i+1] if i+1 < len(nvidia_smi.split('\n')) else ""
                    gpu_lines.append(next_line)
            
            for line in gpu_lines:
                print(f"  {line.strip()}")
        
    except subprocess.CalledProcessError:
        print("未检测到NVIDIA驱动")
        print("提示: 如果您有NVIDIA显卡，请安装最新驱动: https://www.nvidia.com/Download/index.aspx")

def check_pytorch_cuda():
    """检查PyTorch的CUDA支持"""
    print_section("PyTorch CUDA支持")
    
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        print(f"CUDA是否可用: {'是' if cuda_available else '否'}")
        
        if cuda_available:
            print(f"PyTorch CUDA版本: {torch.version.cuda}")
            print(f"当前设备: {torch.cuda.get_device_name(0)}")
            print(f"GPU数量: {torch.cuda.device_count()}")
            
            # 显示所有GPU
            if torch.cuda.device_count() > 1:
                print("\n可用GPU列表:")
                for i in range(torch.cuda.device_count()):
                    print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
            
            # 显示显存信息
            print("\n显存信息:")
            for i in range(torch.cuda.device_count()):
                total_mem = torch.cuda.get_device_properties(i).total_memory / 1024 / 1024 / 1024
                print(f"  GPU {i} 总显存: {total_mem:.2f} GB")
                
            # 测试CUDA功能
            try:
                print("\n执行简单CUDA运算测试...")
                x = torch.rand(5, 3).cuda()
                y = torch.rand(5, 3).cuda()
                z = x + y
                print(f"测试结果: {'成功' if z.device.type == 'cuda' else '失败'}")
            except Exception as e:
                print(f"测试失败: {e}")
        else:
            print("PyTorch未检测到CUDA，可能的原因:")
            print("  1. 未安装NVIDIA驱动")
            print("  2. 安装的PyTorch版本不支持CUDA")
            print("  3. CUDA版本与PyTorch不兼容")
            
            print("\n建议解决方案:")
            print("  1. 确保安装了NVIDIA驱动")
            print("  2. 安装CUDA Toolkit")
            print("  3. 重新安装支持CUDA的PyTorch: https://pytorch.org/get-started/locally/")
    
    except ImportError:
        print("未安装PyTorch")
        print("请使用以下命令安装支持CUDA的PyTorch:")
        print("  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")

def print_cuda_device_info():
    """打印CUDA设备信息"""
    try:
        import torch
        if torch.cuda.is_available():
            print_section("CUDA设备详细信息")
            for i in range(torch.cuda.device_count()):
                device_properties = torch.cuda.get_device_properties(i)
                print(f"\nGPU {i}: {device_properties.name}")
                print(f"  总显存: {device_properties.total_memory / 1024 / 1024 / 1024:.2f} GB")
                print(f"  流处理器数量: {device_properties.multi_processor_count}")
                print(f"  计算能力: {device_properties.major}.{device_properties.minor}")
                print(f"  最大线程数/块: {device_properties.max_threads_per_block}")
                print(f"  最大共享内存/块: {device_properties.max_shared_memory_per_block / 1024:.2f} KB")
    except:
        pass

def main():
    """主函数"""
    print_header("CUDA和PyTorch环境检测工具")
    print("此工具检测您的系统CUDA环境和PyTorch配置，以确保松瓷机电AI助手能正常运行。")
    
    check_python()
    check_pip_packages()
    check_cuda()
    check_pytorch_cuda()
    print_cuda_device_info()
    
    print_section("检测结果总结")
    try:
        import torch
        cuda_ready = torch.cuda.is_available()
        
        if cuda_ready:
            print("✅ 您的系统已正确配置CUDA和PyTorch")
            print("   松瓷机电AI助手可以使用GPU加速运行。")
        else:
            print("⚠️ 未检测到可用的CUDA环境")
            print("   松瓷机电AI助手将使用CPU模式运行，性能可能受限。")
    except ImportError:
        print("❌ 未安装PyTorch")
        print("   请先安装PyTorch后再运行松瓷机电AI助手。")
    
    print("\n" + "=" * 60)
    print(" 检测完成 ".center(60, "="))
    print("=" * 60)

if __name__ == "__main__":
    main() 