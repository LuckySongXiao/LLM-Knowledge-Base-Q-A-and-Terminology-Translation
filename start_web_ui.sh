#!/bin/bash

# 松瓷机电AI助手 WEB UI 启动脚本 (Linux/macOS)

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    松瓷机电AI助手 WEB UI 启动脚本                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

echo "[INFO] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] 未找到Python3，请确保Python3已安装"
    exit 1
fi

echo "[INFO] 检查WEB UI依赖..."
if ! python3 -c "import flask" &> /dev/null; then
    echo "[INFO] 安装WEB UI依赖包..."
    pip3 install -r web_ui/requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] 依赖安装失败"
        exit 1
    fi
fi

echo "[INFO] 启动WEB UI服务..."
echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  WEB UI服务即将启动                                          ║"
echo "║  本地访问: http://localhost:5000                             ║"
echo "║  局域网访问: http://[您的IP]:5000                            ║"
echo "║  按 Ctrl+C 停止服务                                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

cd "$(dirname "$0")"
python3 web_ui/app.py

echo
echo "[INFO] WEB UI服务已停止"
