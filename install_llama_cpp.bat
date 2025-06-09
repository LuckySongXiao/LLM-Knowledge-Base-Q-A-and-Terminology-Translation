@echo off
chcp 65001 >nul
title 安装llama-cpp-python

echo [信息] 正在安装预编译的llama-cpp-python包...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple llama-cpp-python --prefer-binary

if %errorlevel% neq 0 (
    echo [警告] 预编译包安装失败，尝试使用特定版本...
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple llama-cpp-python==0.2.56+cpuavx2
)

echo [信息] 安装完成，按任意键退出...
pause>nul