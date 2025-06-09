@echo off
chcp 65001 >nul
title 松瓷机电AI助手一体化打包工具

echo ============================================================
echo               松瓷机电AI助手一体化打包工具 
echo ============================================================
echo.
echo 此脚本将松瓷机电AI助手应用与虚拟环境一起打包成可执行文件
echo.

:: 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请确保已安装Python环境
    pause
    exit /b 1
)

:: 检查是否在conda环境中
set IS_CONDA=0
if defined CONDA_PREFIX (
    set IS_CONDA=1
    echo [信息] 检测到Conda环境: %CONDA_PREFIX%
    for /f "tokens=* USEBACKQ" %%F in (`conda info --envs ^| findstr "*"`) do (
        set ENV_INFO=%%F
    )
    for /f "tokens=1" %%A in ("!ENV_INFO!") do (
        set ENV_NAME=%%A
    )
    echo [信息] 当前激活的环境: !ENV_NAME!
) else (
    echo [信息] 检测到标准Python虚拟环境
)

echo.
echo [信息] 确保安装必要的依赖...
python -m pip install pyinstaller > nul

:: 设置默认选项
set APP_NAME=松瓷机电AI助手
set APP_VERSION=1.0.0
set INCLUDE_MODELS=0
set CREATE_INSTALLER=1
set MAIN_SCRIPT=AI_assistant.py

:: 获取用户选项
echo.
echo 请设置打包选项:
echo ----------------------------

set /p APP_NAME_INPUT=应用名称 [%APP_NAME%]: 
if not "%APP_NAME_INPUT%"=="" set APP_NAME=%APP_NAME_INPUT%

set /p APP_VERSION_INPUT=应用版本 [%APP_VERSION%]: 
if not "%APP_VERSION_INPUT%"=="" set APP_VERSION=%APP_VERSION_INPUT%

echo.
echo 是否包含模型文件? (将大幅增加包体积)
echo 1. 不包含 [默认]
echo 2. 包含
set /p INCLUDE_MODELS_INPUT=请选择 [1-2]: 
if "%INCLUDE_MODELS_INPUT%"=="2" set INCLUDE_MODELS=1

echo.
echo 是否创建Windows安装程序?
echo 1. 创建 [默认]
echo 2. 不创建
set /p CREATE_INSTALLER_INPUT=请选择 [1-2]: 
if "%CREATE_INSTALLER_INPUT%"=="2" set CREATE_INSTALLER=0

:: 确认设置
echo.
echo ============================================================
echo               打包设置确认
echo ============================================================
echo 应用名称: %APP_NAME%
echo 应用版本: %APP_VERSION%
echo 包含模型文件: %INCLUDE_MODELS% (0=否, 1=是)
echo 创建安装程序: %CREATE_INSTALLER% (0=否, 1=是)
echo.
echo 确认以上设置并开始打包? (Y/N)
set /p CONFIRM=
if /i not "%CONFIRM%"=="Y" (
    echo 已取消打包操作
    pause
    exit /b 0
)

:: 构建命令行参数
set CMD_ARGS=--name "%APP_NAME%" --version "%APP_VERSION%"

if %INCLUDE_MODELS%==1 (
    set CMD_ARGS=%CMD_ARGS% --include-models
)

if %CREATE_INSTALLER%==0 (
    set CMD_ARGS=%CMD_ARGS% --no-installer
)

:: 执行打包脚本
echo.
echo [信息] 开始打包过程...
python package_app.py %CMD_ARGS%

if %errorlevel% neq 0 (
    echo [错误] 打包过程失败，请查看日志以获取详细信息
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo               打包完成!
echo ============================================================
echo 可执行文件位于: dist\%APP_NAME%\%APP_NAME%.exe
if %CREATE_INSTALLER%==1 echo 安装程序位于: %APP_NAME%_Setup_v%APP_VERSION%.exe
echo.
echo 按任意键退出...
pause > nul 