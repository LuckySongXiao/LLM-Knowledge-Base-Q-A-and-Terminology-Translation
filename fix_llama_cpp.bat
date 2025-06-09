@echo off
chcp 65001 >nul
title 修复llama-cpp-python安装

echo [信息] 卸载现有的llama-cpp-python...
pip uninstall -y llama-cpp-python

echo [信息] 清理pip缓存...
pip cache purge

echo [信息] 重新安装llama-cpp-python...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple llama-cpp-python==0.2.56+cpuavx2

echo [信息] 验证安装...
python -c "from llama_cpp import Llama; print('llama_cpp导入成功!')"

if %errorlevel% neq 0 (
    echo [错误] llama_cpp模块导入失败，尝试安装最新版本...
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple llama-cpp-python --prefer-binary
    python -c "from llama_cpp import Llama; print('llama_cpp导入成功!')"
)

echo [信息] 安装完成，按任意键退出...
pause>nul