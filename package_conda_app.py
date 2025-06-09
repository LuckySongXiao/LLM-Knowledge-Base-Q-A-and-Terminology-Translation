#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
package_conda_app.py - 松瓷机电AI助手应用与Conda环境一体化打包工具

此脚本用于将松瓷机电AI助手应用程序与特定的Conda环境一起打包成独立可执行文件，
能够自动检测Conda环境、收集依赖、模型文件和资源，生成可执行文件和安装程序。
"""

import os
import sys
import json
import shutil
import logging
import argparse
import platform
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('package_conda_app')

# 全局变量
APP_NAME = "松瓷机电AI助手"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "AI_assistant.py"
SPEC_FILE = "ai_assistant_conda_bundle.spec"
OUTPUT_DIR = "dist"
BUILD_DIR = "build"
TEMP_DIR = tempfile.mkdtemp(prefix="ai_assistant_conda_bundle_")
ICON_PATH = "icon.ico"  # 图标文件路径，如果存在
DEFAULT_CONDA_ENV = "vllm_env"

class CondaPackageManager:
    """Conda环境打包管理器类，处理松瓷机电AI助手应用程序与Conda环境的一体化打包"""
    
    def __init__(self, args: Dict[str, Any]):
        """
        初始化Conda打包管理器
        
        Args:
            args: 包含各种配置选项的字典
        """
        self.args = args
        self.app_name = args.get('app_name', APP_NAME)
        self.app_version = args.get('app_version', APP_VERSION)
        self.main_script = args.get('main_script', MAIN_SCRIPT)
        self.output_dir = args.get('output_dir', OUTPUT_DIR)
        self.include_models = args.get('include_models', False)
        self.conda_env = args.get('conda_env', DEFAULT_CONDA_ENV)
        self.create_installer = args.get('create_installer', True)
        self.conda_prefix = ""
        self.env_site_packages = ""
        self.data_files = []
        self.hidden_imports = []
        self.conda_packages = []
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(BUILD_DIR, exist_ok=True)
    
    def detect_conda_env(self) -> bool:
        """
        检测指定的Conda环境
        
        Returns:
            bool: 环境检测是否成功
        """
        logger.info(f"检测Conda环境: {self.conda_env}")
        
        try:
            # 列出所有conda环境
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 解析JSON输出
            env_data = json.loads(result.stdout)
            env_paths = {os.path.basename(path): path for path in env_data.get('envs', [])}
            
            # 获取目标环境路径
            if self.conda_env in env_paths:
                self.conda_prefix = env_paths[self.conda_env]
            else:
                # 尝试精确匹配
                for path in env_data.get('envs', []):
                    if os.path.basename(path) == self.conda_env:
                        self.conda_prefix = path
                        break
            
            if not self.conda_prefix:
                logger.error(f"未找到Conda环境: {self.conda_env}")
                logger.info("可用的Conda环境:")
                for env in env_paths:
                    logger.info(f"  - {env}")
                return False
            
            logger.info(f"找到Conda环境路径: {self.conda_prefix}")
            
            # 设置site-packages路径
            if platform.system() == 'Windows':
                self.env_site_packages = os.path.join(self.conda_prefix, "Lib", "site-packages")
            else:
                # 查找Python版本
                python_dirs = [d for d in os.listdir(os.path.join(self.conda_prefix, "lib")) 
                              if d.startswith("python")]
                if python_dirs:
                    python_dir = python_dirs[0]
                    self.env_site_packages = os.path.join(self.conda_prefix, "lib", python_dir, "site-packages")
                else:
                    # 假设Python 3.9
                    self.env_site_packages = os.path.join(self.conda_prefix, "lib", "python3.9", "site-packages")
            
            logger.info(f"site-packages路径: {self.env_site_packages}")
            
            if not os.path.exists(self.env_site_packages):
                logger.error(f"site-packages路径不存在: {self.env_site_packages}")
                return False
            
            return True
        
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"检测Conda环境失败: {e}")
            return False
    
    def collect_conda_packages(self) -> bool:
        """
        收集Conda环境中的包
        
        Returns:
            bool: 收集是否成功
        """
        logger.info(f"收集Conda环境 {self.conda_env} 中的包...")
        
        try:
            # 获取conda包列表
            result = subprocess.run(
                ["conda", "list", "--name", self.conda_env, "--json"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 解析JSON输出
            packages = json.loads(result.stdout)
            
            # 提取包名称
            for package in packages:
                pkg_name = package.get('name', '')
                if pkg_name and pkg_name != 'python':
                    self.conda_packages.append(pkg_name)
                    self.hidden_imports.append(pkg_name)
            
            logger.info(f"收集了 {len(self.conda_packages)} 个Conda包")
            
            # 添加常见隐藏导入
            common_imports = [
                'numpy', 'scipy', 'sklearn', 'torch', 'torchaudio', 'torchvision',
                'transformers', 'accelerate', 'sentence_transformers', 'PySide6',
                'jieba', 'modelscope', 'PIL', 'json', 'yaml', 'pyyaml', 'cv2', 'pandas'
            ]
            
            for imp in common_imports:
                if imp not in self.hidden_imports:
                    self.hidden_imports.append(imp)
            
            # 确保PyInstaller已安装
            logger.info("安装PyInstaller...")
            subprocess.run(
                ["conda", "install", "-n", self.conda_env, "-y", "pyinstaller"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return True
        
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"收集Conda包失败: {e}")
            return False
    
    def collect_data_files(self) -> bool:
        """
        收集应用程序数据文件
        
        Returns:
            bool: 收集数据文件是否成功
        """
        logger.info("收集数据文件...")
        
        # 添加配置文件
        if os.path.exists('config.json'):
            self.data_files.append(('config.json', 'config.json', 'DATA'))
        
        # 添加README和文档
        for readme in ['README.md', 'CHANGELOG.md', 'LICENSE']:
            if os.path.exists(readme):
                self.data_files.append((readme, readme, 'DATA'))
        
        # 添加数据目录
        data_dirs = [
            'data',
            os.path.join('data', 'knowledge'),
            os.path.join('data', 'terms'),
            os.path.join('data', 'vectors'),
            os.path.join('data', 'term_vectors')
        ]
        
        # 创建数据目录
        for data_dir in data_dirs:
            os.makedirs(os.path.join(TEMP_DIR, data_dir), exist_ok=True)
            self.data_files.append((data_dir, os.path.join(TEMP_DIR, data_dir), 'DATA'))
        
        # 添加模型文件(如果指定)
        if self.include_models:
            logger.info("收集模型文件...")
            model_dirs = ['QWEN', 'BAAI']
            for model_dir in model_dirs:
                if os.path.exists(model_dir):
                    # 遍历模型目录下的所有文件和子目录
                    for root, dirs, files in os.walk(model_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path)
                            self.data_files.append((relative_path, file_path, 'DATA'))
                    
                    # 输出模型文件总数
                    logger.info(f"从 {model_dir} 收集了模型文件")
        
        # 添加批处理脚本和工具脚本
        script_files = [
            'check_cuda.py',
            'create_data_dirs.py',
            'simple_embedding.py'
        ]
        for script in script_files:
            if os.path.exists(script):
                self.data_files.append((script, script, 'DATA'))
        
        logger.info(f"收集了 {len(self.data_files)} 个数据文件")
        return True
    
    def generate_app_info(self) -> Dict:
        """
        生成应用程序信息
        
        Returns:
            Dict: 应用程序信息字典
        """
        logger.info("生成应用程序信息...")
        
        app_info = {
            "name": self.app_name,
            "version": self.app_version,
            "main_script": self.main_script,
            "platform": platform.system(),
            "conda_env": self.conda_env,
            "build_timestamp": str(int(time.time()))
        }
        
        # 获取Python版本
        try:
            result = subprocess.run(
                ["conda", "run", "-n", self.conda_env, "python", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            version_output = result.stdout or result.stderr
            app_info["python_version"] = version_output.strip().split(' ')[1]
        except:
            app_info["python_version"] = "未知"
        
        # 将应用信息保存到临时文件
        app_info_path = os.path.join(TEMP_DIR, "app_info.json")
        with open(app_info_path, "w", encoding="utf-8") as f:
            json.dump(app_info, f, ensure_ascii=False, indent=2)
        
        # 添加到数据文件
        self.data_files.append(("app_info.json", app_info_path, 'DATA'))
        
        logger.info(f"应用程序信息: {app_info}")
        return app_info
    
    def generate_conda_spec_file(self) -> str:
        """
        生成包含Conda环境信息的PyInstaller规格文件
        
        Returns:
            str: 生成的规格文件路径
        """
        logger.info("生成PyInstaller规格文件...")
        
        # 定义基本内容
        spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Conda环境信息
conda_env_name = {repr(self.conda_env)}
conda_env_prefix = {repr(self.conda_prefix)}
site_packages_path = {repr(self.env_site_packages)}

# 隐藏导入
hidden_imports = {repr(self.hidden_imports)}

# 基础分析
a = Analysis(
    ['{self.main_script}'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
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
        for dest, src, file_type in self.data_files:
            spec_content += f"a.datas += [('{dest}', r'{src}', '{file_type}')]\n"
        
        # 添加图标支持
        icon_option = ""
        if os.path.exists(ICON_PATH):
            icon_option = f", icon='{ICON_PATH}'"
        
        # 完成规格文件
        spec_content += f"""
# 添加核心模块目录
if os.path.exists('core'):
    a.datas += collect_data_files('core')
    
# 添加UI模块目录
if os.path.exists('ui'):
    a.datas += collect_data_files('ui')
    
# 添加utils目录
if os.path.exists('utils'):
    a.datas += collect_data_files('utils')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.app_name}',
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
        
        logger.info(f"规格文件已生成: {SPEC_FILE}")
        return SPEC_FILE
    
    def build_conda_executable(self) -> bool:
        """
        通过Conda环境构建可执行文件
        
        Returns:
            bool: 构建是否成功
        """
        logger.info("开始通过Conda环境构建可执行文件...")
        
        try:
            # 构建命令
            cmd = [
                "conda", "run",
                "--name", self.conda_env,
                "python", "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                SPEC_FILE
            ]
            
            # 执行构建
            logger.info(f"执行命令: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 输出构建日志
            log_path = os.path.join(TEMP_DIR, "build_log.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(process.stdout)
                f.write("\n\n")
                f.write(process.stderr)
            
            logger.info(f"构建日志已保存至: {log_path}")
            logger.info("构建完成!")
            
            # 清理临时文件
            try:
                if os.path.exists(BUILD_DIR):
                    shutil.rmtree(BUILD_DIR)
                if os.path.exists(SPEC_FILE):
                    os.remove(SPEC_FILE)
            except:
                logger.warning("清理临时文件失败")
            
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"构建失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            return False
    
    def create_windows_installer(self) -> bool:
        """
        创建Windows安装程序
        
        Returns:
            bool: 创建安装程序是否成功
        """
        if platform.system() != "Windows" or not self.create_installer:
            logger.info("跳过创建安装程序")
            return True
        
        logger.info("创建Windows安装程序...")
        
        try:
            # 检查NSIS是否安装
            try:
                subprocess.run(
                    ["makensis", "/VERSION"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.warning("未安装NSIS或未添加到PATH，跳过创建安装程序")
                return False
            
            # 创建NSIS脚本
            nsis_script = """
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
  
  ; 创建桌面快捷方式
  CreateShortCut "$DESKTOP\\{app_name}.lnk" "$INSTDIR\\{exe_name}" "" "$INSTDIR\\{icon_name}" 0
  
  ; 注册卸载信息
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayName" "{app_name}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "UninstallString" "$INSTDIR\\uninstall.exe"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayIcon" "$INSTDIR\\{icon_name}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayVersion" "{app_version}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "Publisher" "AI Assistant Team"
  
  ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "EstimatedSize" "$0"
SectionEnd

; 卸载部分
Section "Uninstall"
  ; 删除安装文件
  RMDir /r "$INSTDIR"
  
  ; 删除开始菜单项
  RMDir /r "$SMPROGRAMS\\{app_name}"
  
  ; 删除桌面快捷方式
  Delete "$DESKTOP\\{app_name}.lnk"
  
  ; 删除注册表项
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"
  DeleteRegKey HKCU "Software\\{app_name}"
SectionEnd
""".format(
                app_name=self.app_name,
                app_version=self.app_version,
                installer_name=f"{self.app_name}_Conda_Setup_v{self.app_version}.exe",
                dist_dir=os.path.join(self.output_dir, self.app_name),
                exe_name=f"{self.app_name}.exe",
                icon_path=ICON_PATH if os.path.exists(ICON_PATH) else "icon.ico",
                icon_name=os.path.basename(ICON_PATH) if os.path.exists(ICON_PATH) else "icon.ico"
            )
            
            # 保存NSIS脚本
            nsis_script_path = os.path.join(TEMP_DIR, "installer.nsi")
            with open(nsis_script_path, "w", encoding="utf-8") as f:
                f.write(nsis_script)
            
            # 运行NSIS编译器
            subprocess.run(
                ["makensis", nsis_script_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("安装程序创建成功!")
            return True
        
        except Exception as e:
            logger.error(f"创建安装程序失败: {e}")
            return False
    
    def run(self) -> bool:
        """
        运行打包过程
        
        Returns:
            bool: 打包是否成功
        """
        # 检测Conda环境
        if not self.detect_conda_env():
            return False
        
        # 收集Conda包
        if not self.collect_conda_packages():
            return False
        
        # 收集数据文件
        if not self.collect_data_files():
            return False
        
        # 生成应用程序信息
        self.generate_app_info()
        
        # 生成Conda特定的规格文件
        self.generate_conda_spec_file()
        
        # 构建可执行文件
        if not self.build_conda_executable():
            return False
        
        # 创建Windows安装程序
        if self.create_installer:
            self.create_windows_installer()
        
        # 清理临时文件
        try:
            shutil.rmtree(TEMP_DIR)
        except:
            logger.warning(f"清理临时目录失败: {TEMP_DIR}")
        
        logger.info(f"打包完成! 输出目录: {self.output_dir}")
        logger.info(f"可执行文件: {os.path.join(self.output_dir, self.app_name, f'{self.app_name}.exe')}")
        if self.create_installer and platform.system() == "Windows":
            logger.info(f"安装程序: {self.app_name}_Conda_Setup_v{self.app_version}.exe")
        
        return True


def parse_arguments() -> Dict:
    """
    解析命令行参数
    
    Returns:
        Dict: 参数字典
    """
    parser = argparse.ArgumentParser(description="松瓷机电AI助手应用与Conda环境一体化打包工具")
    parser.add_argument("--name", type=str, help=f"应用程序名称 (默认: {APP_NAME})")
    parser.add_argument("--version", type=str, help=f"应用程序版本 (默认: {APP_VERSION})")
    parser.add_argument("--main", type=str, help=f"主脚本路径 (默认: {MAIN_SCRIPT})")
    parser.add_argument("--output", type=str, help=f"输出目录 (默认: {OUTPUT_DIR})")
    parser.add_argument("--include-models", action="store_true", help="是否包含模型文件 (大幅增加包体积)")
    parser.add_argument("--conda-env", type=str, help=f"指定Conda环境名称 (默认: {DEFAULT_CONDA_ENV})")
    parser.add_argument("--no-installer", action="store_true", help="不创建安装程序")
    
    args = parser.parse_args()
    
    # 构建参数字典
    arguments = {
        "app_name": args.name or APP_NAME,
        "app_version": args.version or APP_VERSION,
        "main_script": args.main or MAIN_SCRIPT,
        "output_dir": args.output or OUTPUT_DIR,
        "include_models": args.include_models,
        "conda_env": args.conda_env or DEFAULT_CONDA_ENV,
        "create_installer": not args.no_installer
    }
    
    return arguments


def main() -> int:
    """
    主函数
    
    Returns:
        int: 退出码
    """
    logger.info(f"开始打包 AI 助手应用程序 (Conda环境版)...")
    
    # 检查conda是否可用
    try:
        subprocess.run(
            ["conda", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("未找到conda命令，请确保已安装Anaconda或Miniconda，并将其添加到PATH")
        return 1
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 创建打包管理器
    manager = CondaPackageManager(args)
    
    # 运行打包过程
    if manager.run():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main()) 