@echo off
chcp 65001 >nul
title 松瓷机电AI助手依赖安装程序

echo ============================================================
echo                  松瓷机电AI助手依赖安装程序
echo ============================================================
echo.
echo 此脚本将使用清华源安装所有必要的依赖包
echo.
echo 注意: 请确保已安装Python 3.9或更高版本
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

:: 安装向量数据库相关依赖
echo.
echo [信息] 安装向量数据库相关依赖...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple sentence-transformers==4.1.0 FlagEmbedding==1.3.4 einops==0.7.0

:: 安装PyTorch (CPU版本，体积较小)
echo.
echo [信息] 安装PyTorch (CPU版本)...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1

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

:: 安装LLM推理引擎
echo.
echo [信息] 安装LLM推理引擎...
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple llama-cpp-python --prefer-binary

echo.
echo ============================================================
echo                    依赖安装完成！
echo ============================================================
echo.
echo 如需GPU加速，请使用install_dependencies_cuda.bat安装GPU版依赖
echo.
echo 按任意键退出...
pause>nul 
