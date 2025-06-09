@echo off
chcp 65001 >nul
title 松瓷机电AI助手Conda环境创建工具

echo ============================================================
echo               松瓷机电AI助手Conda环境创建工具
echo ============================================================
echo.
echo 此脚本将创建一个名为vllm_env的conda虚拟环境，并安装所有依赖
echo.
echo 注意: 
echo   1. 请确保已安装Anaconda或Miniconda
echo   2. 如有NVIDIA显卡，请确保已安装对应驱动
echo.

:: 设置默认环境名和Python版本
set ENV_NAME=vllm_env
set PYTHON_VERSION=3.9

:: 获取命令行参数
if not "%~1"=="" (
    set ENV_NAME=%~1
)

echo 将创建环境: %ENV_NAME% (Python %PYTHON_VERSION%)
echo.
echo 是否继续? (Y/N)
set /p CONFIRM=

if /i "%CONFIRM%" neq "Y" (
    echo 已取消操作
    exit /b 0
)

:: 检查conda是否可用
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到conda，请确保已安装Anaconda或Miniconda
    goto :EOF
)

:: 检测NVIDIA GPU
echo [信息] 检测NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未检测到NVIDIA GPU或驱动未正确安装
    echo 将创建CPU版环境
    set CUDA_AVAILABLE=0
) else (
    echo [信息] 已检测到NVIDIA GPU
    set CUDA_AVAILABLE=1
)

:: 创建conda环境
echo.
echo [信息] 正在创建conda环境 %ENV_NAME%...
call conda create -n %ENV_NAME% python=%PYTHON_VERSION% -y

:: 激活环境
echo.
echo [信息] 激活环境 %ENV_NAME%...
call conda activate %ENV_NAME%

:: 安装基础依赖
echo.
echo [信息] 使用清华源安装基础依赖...
call conda install -c conda-forge -y numpy=1.24.3

:: 安装pip依赖
echo.
echo [信息] 安装PySide6界面库...
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6==6.9.0

:: 安装大模型相关依赖
echo.
echo [信息] 安装大模型相关依赖...
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers==4.51.3 accelerate==1.6.0 optimum==1.24.0
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple safetensors==0.5.3 peft==0.5.0
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple auto-gptq==0.7.1 bitsandbytes==0.45.5

:: 安装向量数据库相关依赖
echo.
echo [信息] 安装向量数据库相关依赖...
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple sentence-transformers==4.1.0 FlagEmbedding==1.3.4 einops==0.7.0

:: 安装PyTorch
echo.
if %CUDA_AVAILABLE%==1 (
    :: 检测CUDA版本
    echo [信息] 检测CUDA版本...
    for /f "tokens=3" %%i in ('nvidia-smi ^| findstr "CUDA Version"') do (
        set CUDA_VERSION=%%i
    )
    echo [信息] 检测到CUDA版本: %CUDA_VERSION%

    :: 根据CUDA版本安装对应的PyTorch
    echo [信息] 安装支持CUDA的PyTorch...
    
    if "%CUDA_VERSION:~0,4%"=="12.3" (
        call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121
    ) else if "%CUDA_VERSION:~0,4%"=="12.1" (
        call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121
    ) else if "%CUDA_VERSION:~0,4%"=="11.8" (
        call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu118 torchvision==0.16.0+cu118 torchaudio==2.1.0+cu118
    ) else if "%CUDA_VERSION:~0,4%"=="11.7" (
        call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.0.1+cu117 torchvision==0.15.2+cu117 torchaudio==2.0.2+cu117
    ) else (
        :: 默认安装CUDA 12.1版本
        echo [警告] 未找到完全匹配的CUDA版本，将安装与CUDA 12.1兼容的PyTorch版本
        call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121
    )
    
    :: 安装CUDA特有的依赖
    call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple bitsandbytes-windows==0.37.5 ctransformers==0.2.27 rwkv==0.4.2
) else (
    :: 安装CPU版本
    echo [信息] 安装CPU版PyTorch...
    call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1
)

:: 安装NLP相关依赖
echo.
echo [信息] 安装NLP相关依赖...
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple jieba==0.42.1 nltk==3.9.1 tokenizers==0.21.1
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple scikit-learn==1.6.1 scipy==1.9.3 pandas==2.2.3

:: 安装文档处理依赖
echo.
echo [信息] 安装文档处理依赖...
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple python-docx==1.1.2 pypdf2==3.0.1 lxml==5.3.2 beautifulsoup4==4.13.3

:: 安装modelscope
echo.
echo [信息] 安装ModelScope...
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple modelscope==1.25.0

:: 安装其他工具依赖
echo.
echo [信息] 安装其他工具依赖...
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests==2.32.3 tqdm==4.67.1 pyperclip==1.9.0
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple psutil==7.0.0 loguru==0.7.3 fsspec==2023.6.0
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple addict==2.4.0 pyyaml==6.0.2 rich==13.7.1
call python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple filelock==3.18.0 packaging==24.2 pillow==11.2.1

:: 验证环境
echo.
echo [信息] 验证环境...
call python -c "import sys, torch; print(f'Python版本: {sys.version}'); print(f'PyTorch版本: {torch.__version__}'); print(f'CUDA是否可用: {torch.cuda.is_available()}'); print(f'GPU数量: {torch.cuda.device_count()}'); print(f'当前设备: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

:: 创建目录结构
echo.
echo [信息] 创建数据目录...
mkdir data\knowledge 2>nul
mkdir data\terms 2>nul
mkdir data\vectors 2>nul
mkdir data\term_vectors 2>nul

echo.
echo ============================================================
echo                 环境创建完成！
echo ============================================================
echo.
echo 使用以下命令激活环境:
echo   conda activate %ENV_NAME%
echo.
echo 使用以下命令运行程序:
echo   python AI_assistant.py
echo.
echo 按任意键退出...
pause>nul 