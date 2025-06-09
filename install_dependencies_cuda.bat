@echo off
chcp 65001 >nul
title 松瓷机电AI助手依赖安装程序 (CUDA支持版)

echo ============================================================
echo            松瓷机电AI助手依赖安装程序 (CUDA支持版)
echo ============================================================
echo.
echo 此脚本将使用清华源安装所有必要的依赖包，包括CUDA支持
echo.
echo 注意: 
echo   1. 请确保已安装Python 3.9或更高版本
echo   2. 请确保已安装NVIDIA驱动和CUDA Toolkit
echo.
echo 开始安装...
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.9或更高版本！
    pause
    exit /b 1
)

echo [信息] 检测到Python已安装
echo.

:: 检测NVIDIA GPU和CUDA
echo [信息] 检测NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未检测到NVIDIA GPU或驱动未正确安装！
    echo 将继续安装，但CUDA可能无法正常工作。
    echo.
    set CUDA_AVAILABLE=0
) else (
    echo [信息] 已检测到NVIDIA GPU
    set CUDA_AVAILABLE=1
    
    :: 检测可用的CUDA版本
    echo [信息] 检测CUDA版本...
    nvidia-smi | findstr "CUDA Version" > cuda_version.txt
    set /p CUDA_VERSION_LINE=<cuda_version.txt
    del cuda_version.txt
    
    :: 提取CUDA版本号
    for /f "tokens=6" %%i in ("%CUDA_VERSION_LINE%") do (
        set CUDA_VERSION=%%i
    )
    
    echo [信息] 检测到CUDA版本: %CUDA_VERSION%
    echo.
)

:: 创建必要的目录结构
echo [信息] 创建数据目录...
mkdir data\knowledge 2>nul
mkdir data\terms 2>nul
mkdir data\vectors 2>nul
mkdir data\term_vectors 2>nul
echo.

:: 使用清华源安装基础依赖
echo [信息] 使用清华源安装基础依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip

:: 安装PySide6
echo.
echo [信息] 安装PySide6界面库...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6==6.9.0

:: 安装大模型相关依赖
echo.
echo [信息] 安装大模型相关依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers==4.51.3 accelerate==1.6.0 optimum==1.24.0
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple safetensors==0.5.3 peft==0.5.0
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple auto-gptq==0.7.1 bitsandbytes==0.45.5

:: 安装向量数据库相关依赖
echo.
echo [信息] 安装向量数据库相关依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple sentence-transformers==4.1.0 FlagEmbedding==1.3.4 einops==0.7.0

:: 安装CUDA版PyTorch
echo.
if %CUDA_AVAILABLE%==1 (
    :: 根据CUDA版本安装对应的PyTorch
    echo [信息] 安装支持CUDA的PyTorch...
    
    :: 根据不同CUDA版本安装
    if "%CUDA_VERSION:~0,4%"=="12.3" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121
    ) else if "%CUDA_VERSION:~0,4%"=="12.1" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121
    ) else if "%CUDA_VERSION:~0,4%"=="11.8" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu118 torchvision==0.16.0+cu118 torchaudio==2.1.0+cu118
    ) else if "%CUDA_VERSION:~0,4%"=="11.7" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.0.1+cu117 torchvision==0.15.2+cu117 torchaudio==2.0.2+cu117
    ) else (
        :: 默认安装CUDA 12.1版本
        echo [警告] 未找到完全匹配的CUDA版本，将安装与CUDA 12.1兼容的PyTorch版本
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121
    )
) else (
    :: 安装CPU版本
    echo [信息] 未检测到CUDA，安装CPU版PyTorch...
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1
)

:: 安装NLP相关依赖
echo.
echo [信息] 安装NLP相关依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple jieba==0.42.1 numpy==1.24.3 nltk==3.9.1 tokenizers==0.21.1
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple scikit-learn==1.6.1 scipy==1.9.3 pandas==2.2.3

:: 安装文档处理依赖
echo.
echo [信息] 安装文档处理依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple python-docx==1.1.2 pypdf2==3.0.1 lxml==5.3.2 beautifulsoup4==4.13.3

:: 安装modelscope(用于语音功能)
echo.
echo [信息] 安装ModelScope相关依赖(用于语音功能)...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple modelscope==1.25.0

:: 安装其他工具依赖
echo.
echo [信息] 安装其他工具依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests==2.32.3 tqdm==4.67.1 pyperclip==1.9.0
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple psutil==7.0.0 loguru==0.7.3 fsspec==2023.6.0

:: 安装可选依赖
echo.
echo [信息] 安装可选依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple addict==2.4.0 pyyaml==6.0.2 rich==13.7.1
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple filelock==3.18.0 packaging==24.2 pillow==11.2.1

:: 安装CUDA特有的依赖
if %CUDA_AVAILABLE%==1 (
    echo.
    echo [信息] 安装CUDA特有依赖...
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple bitsandbytes-windows==0.37.5 ctransformers==0.2.27 rwkv==0.4.2
)

:: 验证PyTorch是否支持CUDA
echo.
echo [信息] 验证PyTorch CUDA支持...
python -c "import torch; print('CUDA是否可用:', torch.cuda.is_available()); print('GPU数量:', torch.cuda.device_count()); print('当前设备:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

echo.
echo ============================================================
echo                    依赖安装完成！
echo ============================================================
echo.
echo 提示：可以使用 python check_cuda.py 来检测CUDA环境和PyTorch配置
echo.
echo 按任意键退出...
pause>nul 