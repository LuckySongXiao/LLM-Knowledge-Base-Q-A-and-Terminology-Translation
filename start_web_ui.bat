@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    松瓷机电AI助手 WEB UI 启动脚本                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo [INFO] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到Python，请确保Python已安装并添加到PATH环境变量
    pause
    exit /b 1
)

echo [INFO] 检查WEB UI依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装WEB UI依赖包...
    pip install -r web_ui\requirements.txt
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [INFO] 启动WEB UI服务...
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║  WEB UI服务即将启动                                          ║
echo ║  本地访问: http://localhost:5000                             ║
echo ║  局域网访问: http://[您的IP]:5000                            ║
echo ║  按 Ctrl+C 停止服务                                          ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"
python web_ui\app.py

echo.
echo [INFO] WEB UI服务已停止
pause
