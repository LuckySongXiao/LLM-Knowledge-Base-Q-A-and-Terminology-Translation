@echo off
chcp 65001 >nul
title 导出Conda环境配置

echo ============================================================
echo                  Conda环境导出工具
echo ============================================================
echo.
echo 此脚本将导出指定的conda环境配置到本地文件
echo.

:: 设置默认环境名称
set ENV_NAME=vllm_env

:: 获取命令行参数
if not "%~1"=="" (
    set ENV_NAME=%~1
)

echo 正在导出环境: %ENV_NAME%
echo.

:: 检查conda是否安装并可用
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到conda命令，请确保已安装conda并添加到环境变量中
    goto :EOF
)

:: 创建输出目录
mkdir conda_export 2>nul

:: 导出完整环境配置
echo [1/3] 导出完整环境配置...
conda --no-plugins env export -n %ENV_NAME% > conda_export\%ENV_NAME%_full.yml

:: 导出不含构建信息的环境配置
echo [2/3] 导出不含构建信息的环境配置...
conda --no-plugins env export -n %ENV_NAME% --no-builds > conda_export\%ENV_NAME%_no_builds.yml

:: 导出仅pip安装的包
echo [3/3] 导出pip安装的包...
echo # pip packages from %ENV_NAME% environment > conda_export\%ENV_NAME%_pip.txt
conda --no-plugins list -n %ENV_NAME% | findstr "pypi" > conda_export\%ENV_NAME%_pip_raw.txt

:: 处理pip包列表，提取包名和版本
python -c "
with open('conda_export/%ENV_NAME%_pip_raw.txt', 'r') as f, open('conda_export/%ENV_NAME%_pip.txt', 'a') as out:
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 3 and parts[1] != '<pip>':
            out.write(f'{parts[0]}=={parts[1]}\n')
"

echo.
echo ============================================================
echo                     导出完成！
echo ============================================================
echo.
echo 导出的文件:
echo   - conda_export\%ENV_NAME%_full.yml     (完整环境配置)
echo   - conda_export\%ENV_NAME%_no_builds.yml (不含构建信息的配置)
echo   - conda_export\%ENV_NAME%_pip.txt      (pip安装的包列表)
echo.
echo 提示: 可以使用以下命令从文件创建相同环境:
echo   conda env create -f conda_export\%ENV_NAME%_no_builds.yml
echo.
echo 按任意键退出...
pause>nul 