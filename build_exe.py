#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_exe.py - 松瓷机电AI助手程序打包工具

此脚本用于将松瓷机电AI助手程序打包成独立的可执行文件和安装程序。
支持自定义打包配置，可选择是否包含模型文件。
"""

import os
import sys
import shutil
import subprocess
import platform
import logging
import json
import time
from typing import Dict, List, Optional, Tuple, Union
import pkg_resources

# 设置日志记录
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('build_exe')

# 全局配置
APP_NAME = "松瓷机电AI助手"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "main.py"  # 应用程序入口脚本
OUTPUT_DIR = "dist"
BUILD_DIR = "build"
SPEC_FILE = "ai_assistant.spec"
INCLUDE_MODELS = False  # 默认不包含模型文件

# 模型相关配置
MODEL_DIR = "models"
MODEL_EXTENSIONS = [".bin", ".onnx", ".pt", ".pth", ".model", ".ckpt", ".safetensors"]

# NSIS安装程序配置
NSIS_TEMPLATE = """
!include "MUI2.nsh"
!include "FileFunc.nsh"

; 应用程序信息
Name "{app_name}"
OutFile "{installer_name}"
InstallDir "$PROGRAMFILES\\{app_name}"
InstallDirRegKey HKCU "Software\\{app_name}" ""

; 界面设置
!define MUI_ABORTWARNING
!define MUI_ICON "{icon_path}"

; 页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"

; 安装部分
Section "安装程序" SecMain
  SetOutPath "$INSTDIR"
  
  ; 复制文件
  File /r "{dist_dir}\\*.*"
  
  ; 创建卸载程序
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  
  ; 创建开始菜单项
  CreateDirectory "$SMPROGRAMS\\{app_name}"
  CreateShortCut "$SMPROGRAMS\\{app_name}\\{app_name}.lnk" "$INSTDIR\\{exe_name}" "" "$INSTDIR\\{icon_name}" 0
  CreateShortCut "$SMPROGRAMS\\{app_name}\\卸载.lnk" "$INSTDIR\\uninstall.exe"
  
  ; 注册卸载信息
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayName" "{app_name}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "UninstallString" "$INSTDIR\\uninstall.exe"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayIcon" "$INSTDIR\\{icon_name}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayVersion" "{app_version}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "Publisher" "AI Assistant Team"
  
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "EstimatedSize" "$0"
SectionEnd

; 卸载部分
Section "Uninstall"
  ; 删除安装文件
  RMDir /r "$INSTDIR"
  
  ; 删除开始菜单项
  RMDir /r "$SMPROGRAMS\\{app_name}"
  
  ; 删除注册表项
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"
  DeleteRegKey HKCU "Software\\{app_name}"
SectionEnd
"""

def check_dependencies() -> bool:
    """
    检查必要的依赖包是否已安装
    
    Returns:
        bool: 所有依赖是否都已安装
    """
    required_packages = ['PyInstaller']
    missing_packages = []
    
    for package in required_packages:
        try:
            pkg_resources.get_distribution(package)
        except pkg_resources.DistributionNotFound:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"缺少必要的依赖包: {', '.join(missing_packages)}")
        logger.info("请使用以下命令安装缺少的依赖:")
        logger.info(f"pip install {' '.join(missing_packages)}")
        return False
    
    logger.info("所有必要的依赖包已安装")
    return True

def create_app_info() -> Dict[str, str]:
    """
    创建应用程序信息
    
    Returns:
        Dict[str, str]: 应用程序信息字典
    """
    app_info = {
        "name": APP_NAME,
        "version": APP_VERSION,
        "main_script": MAIN_SCRIPT,
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "build_timestamp": str(int(time.time()))
    }
    
    # 将应用信息保存到文件
    with open("app_info.json", "w", encoding="utf-8") as f:
        json.dump(app_info, f, ensure_ascii=False, indent=2)
    
    logger.info(f"已创建应用程序信息: {app_info}")
    return app_info

def find_model_files() -> List[str]:
    """
    查找所有模型文件
    
    Returns:
        List[str]: 模型文件路径列表
    """
    model_files = []
    
    if not os.path.exists(MODEL_DIR):
        logger.warning(f"模型目录 '{MODEL_DIR}' 不存在")
        return model_files
    
    for root, _, files in os.walk(MODEL_DIR):
        for file in files:
            if any(file.endswith(ext) for ext in MODEL_EXTENSIONS):
                model_files.append(os.path.join(root, file))
    
    logger.info(f"找到 {len(model_files)} 个模型文件")
    return model_files

def prepare_files() -> Tuple[List[str], Dict[str, str]]:
    """
    准备打包所需的文件
    
    Returns:
        Tuple[List[str], Dict[str, str]]: 
            - 要包含的文件列表
            - 其他资源文件字典
    """
    # 基本文件列表 - 始终包含
    files_to_include = [MAIN_SCRIPT, "app_info.json"]
    
    # 检查并添加图标文件
    icon_path = "icon.ico"
    if not os.path.exists(icon_path):
        logger.warning(f"图标文件 '{icon_path}' 不存在，将使用默认图标")
        icon_path = None
    else:
        files_to_include.append(icon_path)
    
    # 检查并添加模型文件
    model_files = []
    if INCLUDE_MODELS:
        model_files = find_model_files()
        files_to_include.extend(model_files)
    
    # 其他资源文件
    resources = {
        "icon": icon_path,
        "models": model_files
    }
    
    logger.info(f"准备文件完成，共 {len(files_to_include)} 个文件")
    return files_to_include, resources

def generate_spec_file(files: List[str], app_info: Dict[str, str], resources: Dict[str, str]) -> str:
    """
    生成PyInstaller规格文件
    
    Args:
        files (List[str]): 要包含的文件列表
        app_info (Dict[str, str]): 应用程序信息
        resources (Dict[str, str]): 资源文件
    
    Returns:
        str: 生成的规格文件路径
    """
    app_name = app_info["name"]
    main_script = app_info["main_script"]
    icon_path = resources["icon"]
    
    # 构建规格文件内容
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{main_script}'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 添加数据文件
"""
    
    # 添加数据文件
    for file in files:
        if file != main_script:
            spec_content += f"a.datas += [('{os.path.basename(file)}', '{file}', 'DATA')]\n"
    
    # 添加模型文件
    if INCLUDE_MODELS and resources["models"]:
        spec_content += "\n# 添加模型文件\n"
        for model_file in resources["models"]:
            rel_path = os.path.relpath(model_file)
            spec_content += f"a.datas += [('{rel_path}', '{model_file}', 'DATA')]\n"
    
    # 完成规格文件
    icon_option = f", icon='{icon_path}'" if icon_path else ""
    spec_content += f"""
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False{icon_option},
)
"""
    
    # 写入规格文件
    with open(SPEC_FILE, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    logger.info(f"已生成规格文件: {SPEC_FILE}")
    return SPEC_FILE

def build_executable(spec_file: str) -> str:
    """
    构建可执行文件
    
    Args:
        spec_file (str): 规格文件路径
    
    Returns:
        str: 构建的可执行文件路径
    """
    logger.info("开始构建可执行文件...")
    
    cmd = ["pyinstaller", "--clean", "--noconfirm", spec_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error("构建可执行文件失败")
        logger.error(f"错误输出: {result.stderr}")
        return ""
    
    # 查找生成的可执行文件
    exe_name = f"{APP_NAME}.exe" if platform.system() == "Windows" else APP_NAME
    exe_path = os.path.join(OUTPUT_DIR, exe_name)
    
    if not os.path.exists(exe_path):
        logger.error(f"未找到生成的可执行文件: {exe_path}")
        return ""
    
    logger.info(f"成功构建可执行文件: {exe_path}")
    return exe_path

def create_installer(exe_path: str, app_info: Dict[str, str], resources: Dict[str, str]) -> str:
    """
    创建安装程序
    
    Args:
        exe_path (str): 可执行文件路径
        app_info (Dict[str, str]): 应用程序信息
        resources (Dict[str, str]): 资源文件
    
    Returns:
        str: 安装程序路径
    """
    # 只在Windows上创建安装程序
    if platform.system() != "Windows":
        logger.info("非Windows系统，跳过创建安装程序")
        return ""
    
    # 检查NSIS是否安装
    try:
        subprocess.run(["makensis", "/VERSION"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("未安装NSIS或未添加到PATH，跳过创建安装程序")
        return ""
    
    logger.info("开始创建安装程序...")
    
    # 准备安装程序配置
    app_name = app_info["name"]
    app_version = app_info["version"]
    installer_name = f"{app_name}_Setup_v{app_version}.exe"
    nsis_script = "installer.nsi"
    icon_name = os.path.basename(resources["icon"]) if resources["icon"] else "icon.ico"
    exe_name = os.path.basename(exe_path)
    
    # 填充NSIS模板
    nsis_content = NSIS_TEMPLATE.format(
        app_name=app_name,
        app_version=app_version,
        installer_name=installer_name,
        dist_dir=OUTPUT_DIR,
        exe_name=exe_name,
        icon_path=resources["icon"] or "icon.ico",
        icon_name=icon_name
    )
    
    # 写入NSIS脚本
    with open(nsis_script, "w", encoding="utf-8") as f:
        f.write(nsis_content)
    
    # 运行NSIS编译器
    cmd = ["makensis", nsis_script]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error("创建安装程序失败")
        logger.error(f"错误输出: {result.stderr}")
        return ""
    
    # 检查安装程序是否生成
    installer_path = installer_name
    if not os.path.exists(installer_path):
        logger.error(f"未找到生成的安装程序: {installer_path}")
        return ""
    
    logger.info(f"成功创建安装程序: {installer_path}")
    return installer_path

def cleanup(keep_files: List[str] = []) -> None:
    """
    清理临时文件
    
    Args:
        keep_files (List[str]): 要保留的文件列表
    """
    logger.info("清理临时文件...")
    
    # 临时文件列表
    temp_files = [
        "app_info.json",
        SPEC_FILE,
        "installer.nsi",
        BUILD_DIR
    ]
    
    for file in temp_files:
        if file in keep_files:
            continue
        
        try:
            if os.path.isdir(file):
                shutil.rmtree(file)
            elif os.path.exists(file):
                os.remove(file)
        except Exception as e:
            logger.warning(f"清理文件 '{file}' 时出错: {e}")
    
    logger.info("清理完成")

def parse_arguments() -> Dict[str, Union[str, bool]]:
    """
    解析命令行参数
    
    Returns:
        Dict[str, Union[str, bool]]: 参数字典
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="松瓷机电AI助手程序打包工具")
    parser.add_argument("--name", type=str, help=f"应用程序名称 (默认: {APP_NAME})")
    parser.add_argument("--version", type=str, help=f"应用程序版本 (默认: {APP_VERSION})")
    parser.add_argument("--main", type=str, help=f"主脚本路径 (默认: {MAIN_SCRIPT})")
    parser.add_argument("--output", type=str, help=f"输出目录 (默认: {OUTPUT_DIR})")
    parser.add_argument("--include-models", action="store_true", help="是否包含模型文件")
    parser.add_argument("--no-installer", action="store_true", help="不创建安装程序")
    parser.add_argument("--no-cleanup", action="store_true", help="不清理临时文件")
    
    args = parser.parse_args()
    
    # 构建参数字典
    arguments = {
        "name": args.name or APP_NAME,
        "version": args.version or APP_VERSION,
        "main_script": args.main or MAIN_SCRIPT,
        "output_dir": args.output or OUTPUT_DIR,
        "include_models": args.include_models or INCLUDE_MODELS,
        "create_installer": not args.no_installer,
        "cleanup": not args.no_cleanup
    }
    
    return arguments

def main() -> int:
    """
    主函数
    
    Returns:
        int: 退出码
    """
    logger.info(f"开始打包 AI 助手程序...")
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 更新全局配置
    global APP_NAME, APP_VERSION, MAIN_SCRIPT, OUTPUT_DIR, INCLUDE_MODELS
    APP_NAME = args["name"]
    APP_VERSION = args["version"]
    MAIN_SCRIPT = args["main_script"]
    OUTPUT_DIR = args["output_dir"]
    INCLUDE_MODELS = args["include_models"]
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 创建应用程序信息
    app_info = create_app_info()
    
    # 准备文件
    files, resources = prepare_files()
    
    # 生成规格文件
    spec_file = generate_spec_file(files, app_info, resources)
    
    # 构建可执行文件
    exe_path = build_executable(spec_file)
    if not exe_path:
        return 1
    
    # 创建安装程序
    installer_path = ""
    if args["create_installer"]:
        installer_path = create_installer(exe_path, app_info, resources)
    
    # 清理临时文件
    if args["cleanup"]:
        keep_files = []
        cleanup(keep_files)
    
    logger.info("打包完成！")
    logger.info(f"可执行文件: {exe_path}")
    if installer_path:
        logger.info(f"安装程序: {installer_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 