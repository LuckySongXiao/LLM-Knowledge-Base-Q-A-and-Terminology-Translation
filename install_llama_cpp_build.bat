@echo off
chcp 65001 >nul
title 编译安装llama-cpp-python

echo [信息] 设置环境变量...
set CMAKE_ARGS=-DLLAMA_STANDALONE=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DGGML_NO_GIT_INFO=ON

echo [信息] 开始安装llama-cpp-python...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple llama-cpp-python --no-binary llama-cpp-python

echo [信息] 安装完成，按任意键退出...
pause>nul