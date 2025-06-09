@echo off
chcp 65001 >nul
title VLLM模型应用框架 - 全依赖安装程序

:: 设置颜色
setlocal EnableDelayedExpansion
set "ESC="
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
  set "ESC=!ESC!%%a"
)

:: 标题
echo !ESC![1;36m============================================================!ESC![0m
echo !ESC![1;36m             VLLM模型应用框架 - 依赖安装程序              !ESC![0m
echo !ESC![1;36m============================================================!ESC![0m
echo.
echo !ESC![1;33m此脚本将安装VLLM模型应用框架所需的全部依赖!ESC![0m
echo !ESC![0m支持中文显示和自动环境检测!ESC![0m
echo.
echo !ESC![1;33m注意事项:!ESC![0m
echo  1. 请确保已安装Python 3.8或更高版本
echo  2. 安装过程可能需要一些时间，请耐心等待
echo  3. 如有NVIDIA显卡，请确保已安装驱动程序
echo.

:: 检查是否以管理员身份运行
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if %errorlevel% neq 0 (
    echo !ESC![1;31m[警告] 此脚本未以管理员身份运行!ESC![0m
    echo !ESC![1;31m某些操作可能需要管理员权限，建议以管理员身份重新运行!ESC![0m
    echo.
    echo 是否继续安装? (Y/N)
    set /p ADMIN_CHOICE=
    if /i "!ADMIN_CHOICE!"=="N" exit /b 1
    echo.
)

:: 检查Python是否安装
echo !ESC![1;36m[1/7] 检查Python环境...!ESC![0m
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo !ESC![1;31m[错误] 未检测到Python，请先安装Python 3.8或更高版本！!ESC![0m
    echo !ESC![0m下载地址: https://www.python.org/downloads/!ESC![0m
    pause
    exit /b 1
)

:: 获取Python版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo !ESC![1;32m[成功] 检测到Python版本: !PYTHON_VERSION!!ESC![0m
echo.

:: 检测CUDA环境
echo !ESC![1;36m[2/7] 检测GPU和CUDA环境...!ESC![0m
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo !ESC![1;33m[警告] 未检测到NVIDIA GPU或驱动未正确安装!ESC![0m
    echo !ESC![0m系统将使用CPU模式运行，性能可能受限!ESC![0m
    set CUDA_DETECTED=0
) else (
    :: 获取CUDA版本
    nvidia-smi | findstr "CUDA Version" > temp_cuda_version.txt
    set /p CUDA_VERSION_LINE=<temp_cuda_version.txt
    del temp_cuda_version.txt
    
    for /f "tokens=6" %%i in ("!CUDA_VERSION_LINE!") do set CUDA_VERSION=%%i
    
    :: 获取GPU名称
    nvidia-smi --query-gpu=name --format=csv,noheader > temp_gpu_name.txt
    set /p GPU_NAME=<temp_gpu_name.txt
    del temp_gpu_name.txt
    
    echo !ESC![1;32m[成功] 检测到NVIDIA GPU: !GPU_NAME!!ESC![0m
    echo !ESC![1;32m[成功] CUDA版本: !CUDA_VERSION!!ESC![0m
    set CUDA_DETECTED=1
)
echo.

:: 创建数据目录
echo !ESC![1;36m[3/7] 创建必要的数据目录...!ESC![0m
mkdir data 2>nul
mkdir data\knowledge 2>nul
mkdir data\terms 2>nul
mkdir data\vectors 2>nul
mkdir data\term_vectors 2>nul
echo !ESC![1;32m[成功] 数据目录创建完成!ESC![0m
echo.

:: 选择安装模式
echo !ESC![1;36m[4/7] 选择安装模式:!ESC![0m
echo !ESC![1;37m1) 自动检测安装 [推荐]!ESC![0m
echo !ESC![1;37m2) CPU版本安装!ESC![0m
echo !ESC![1;37m3) GPU版本安装 (CUDA支持)!ESC![0m
echo !ESC![1;37m4) 最小化安装 (仅基本功能)!ESC![0m
echo.
set /p INSTALL_MODE=!ESC![1;37m请选择安装模式 [1-4]: !ESC![0m

:: 根据选择设置安装标志
if "!INSTALL_MODE!"=="1" (
    if !CUDA_DETECTED!==1 (
        set INSTALL_GPU=1
        set INSTALL_MIN=0
        echo !ESC![1;32m[选择] 自动检测到GPU，将安装CUDA支持版本!ESC![0m
    ) else (
        set INSTALL_GPU=0
        set INSTALL_MIN=0
        echo !ESC![1;32m[选择] 未检测到GPU，将安装CPU版本!ESC![0m
    )
) else if "!INSTALL_MODE!"=="2" (
    set INSTALL_GPU=0
    set INSTALL_MIN=0
    echo !ESC![1;32m[选择] 将安装CPU版本!ESC![0m
) else if "!INSTALL_MODE!"=="3" (
    set INSTALL_GPU=1
    set INSTALL_MIN=0
    echo !ESC![1;32m[选择] 将安装GPU版本 (CUDA支持)!ESC![0m
    
    if !CUDA_DETECTED!==0 (
        echo !ESC![1;33m[警告] 未检测到CUDA环境，GPU加速可能无法正常工作!ESC![0m
        echo 是否继续安装GPU版本? (Y/N)
        set /p GPU_CHOICE=
        if /i "!GPU_CHOICE!"=="N" (
            set INSTALL_GPU=0
            echo !ESC![1;32m[选择] 已切换为CPU版本安装!ESC![0m
        )
    )
) else if "!INSTALL_MODE!"=="4" (
    set INSTALL_GPU=0
    set INSTALL_MIN=1
    echo !ESC![1;32m[选择] 将安装最小化版本 (仅基本功能)!ESC![0m
) else (
    echo !ESC![1;31m[错误] 无效的选择，将使用默认选项 (自动检测)!ESC![0m
    if !CUDA_DETECTED!==1 (
        set INSTALL_GPU=1
        set INSTALL_MIN=0
    ) else (
        set INSTALL_GPU=0
        set INSTALL_MIN=0
    )
)
echo.

:: 开始安装依赖
echo !ESC![1;36m[5/7] 升级pip并设置国内源...!ESC![0m
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
echo !ESC![1;32m[成功] pip已升级!ESC![0m
echo.

echo !ESC![1;36m[6/7] 安装依赖包...!ESC![0m

:: 安装基础UI依赖
echo !ESC![1;37m安装PySide6界面库...!ESC![0m
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6==6.9.0
echo !ESC![1;32m[成功] PySide6界面库安装完成!ESC![0m

:: 安装基础NLP依赖
echo !ESC![1;37m安装基础NLP依赖...!ESC![0m
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple jieba==0.42.1 numpy==1.24.3 pandas==2.2.3
echo !ESC![1;32m[成功] 基础NLP依赖安装完成!ESC![0m

:: 安装大模型依赖
echo !ESC![1;37m安装大模型基础依赖...!ESC![0m
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers==4.51.3 accelerate==1.6.0
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple safetensors==0.5.3 peft==0.5.0
echo !ESC![1;32m[成功] 大模型基础依赖安装完成!ESC![0m

:: 安装向量模型依赖
echo !ESC![1;37m安装向量模型依赖...!ESC![0m
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple sentence-transformers==4.1.0 FlagEmbedding==1.3.4 einops==0.7.0
echo !ESC![1;32m[成功] 向量模型依赖安装完成!ESC![0m

:: 根据选择安装PyTorch
echo !ESC![1;37m安装PyTorch...!ESC![0m
if !INSTALL_GPU!==1 (
    :: 根据CUDA版本安装对应的PyTorch
    if "!CUDA_VERSION:~0,4!"=="12.3" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121
    ) else if "!CUDA_VERSION:~0,4!"=="12.1" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121
    ) else if "!CUDA_VERSION:~0,4!"=="11.8" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu118 torchvision==0.16.0+cu118 torchaudio==2.1.0+cu118
    ) else if "!CUDA_VERSION:~0,4!"=="11.7" (
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.0.1+cu117 torchvision==0.15.2+cu117 torchaudio==2.0.2+cu117
    ) else (
        echo !ESC![1;33m[警告] 未找到完全匹配的CUDA版本，将安装与CUDA 12.1兼容的PyTorch版本!ESC![0m
        python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121
    )
    echo !ESC![1;32m[成功] 支持CUDA的PyTorch安装完成!ESC![0m
    
    :: 安装GPU特有依赖
    echo !ESC![1;37m安装GPU特有依赖...!ESC![0m
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple auto-gptq==0.7.1 bitsandbytes==0.45.5
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple bitsandbytes-windows==0.37.5 ctransformers==0.2.27
    echo !ESC![1;32m[成功] GPU特有依赖安装完成!ESC![0m
) else (
    :: 安装CPU版PyTorch
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1
    echo !ESC![1;32m[成功] CPU版PyTorch安装完成!ESC![0m
)

:: 安装其他依赖
if !INSTALL_MIN!==0 (
    :: 完整安装
    echo !ESC![1;37m安装文档处理依赖...!ESC![0m
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple python-docx==1.1.2 pypdf2==3.0.1 lxml==5.3.2 beautifulsoup4==4.13.3
    echo !ESC![1;32m[成功] 文档处理依赖安装完成!ESC![0m
    
    echo !ESC![1;37m安装扩展NLP依赖...!ESC![0m
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple nltk==3.9.1 tokenizers==0.21.1 sentencepiece==0.2.0
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple scikit-learn==1.6.1 scipy==1.9.3 regex==2024.11.6
    echo !ESC![1;32m[成功] 扩展NLP依赖安装完成!ESC![0m
    
    echo !ESC![1;37m安装ModelScope依赖...!ESC![0m
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple modelscope==1.25.0
    echo !ESC![1;32m[成功] ModelScope依赖安装完成!ESC![0m
    
    echo !ESC![1;37m安装工具依赖...!ESC![0m
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests==2.32.3 tqdm==4.67.1 pyperclip==1.9.0
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple psutil==7.0.0 loguru==0.7.3 fsspec==2023.6.0
    echo !ESC![1;32m[成功] 工具依赖安装完成!ESC![0m
    
    echo !ESC![1;37m安装可选工具依赖...!ESC![0m
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple addict==2.4.0 pyyaml==6.0.2 rich==13.7.1
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple filelock==3.18.0 packaging==24.2 pillow==11.2.1
    echo !ESC![1;32m[成功] 可选工具依赖安装完成!ESC![0m
) else (
    :: 最小化安装
    echo !ESC![1;37m安装最小必要依赖...!ESC![0m
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests==2.32.3 tqdm==4.67.1
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple filelock==3.18.0 packaging==24.2
    echo !ESC![1;32m[成功] 最小必要依赖安装完成!ESC![0m
)

:: 验证安装
echo !ESC![1;36m[7/7] 验证安装...!ESC![0m

python -c "import torch; import transformers; import PySide6; print('PyTorch版本:', torch.__version__); print('Transformers版本:', transformers.__version__); print('PySide6版本:', PySide6.__version__); print('CUDA是否可用:', torch.cuda.is_available()); print('GPU数量:', torch.cuda.device_count()); print('当前设备:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

:: 安装完成
echo.
echo !ESC![1;36m============================================================!ESC![0m
echo !ESC![1;36m                    依赖安装完成！                          !ESC![0m
echo !ESC![1;36m============================================================!ESC![0m
echo.
echo !ESC![1;32m所有必要依赖已成功安装。!ESC![0m
echo.
echo !ESC![1;37m提示:!ESC![0m
echo  - 您可以使用 !ESC![1;33mpython check_cuda.py!ESC![0m 检测CUDA环境和PyTorch配置
echo  - 使用 !ESC![1;33mpython AI_assistant.py!ESC![0m 运行应用程序
echo.
echo !ESC![1;37m按任意键退出...!ESC![0m
pause>nul 