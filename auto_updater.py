#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_updater.py - 松瓷机电AI助手程序自动更新工具

此脚本用于自动检查、下载和安装松瓷机电AI助手程序的更新。
支持增量更新和全量更新两种模式。
"""

import os
import sys
import json
import time
import shutil
import logging
import hashlib
import requests
import tempfile
import subprocess
import threading
import zipfile
from typing import Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime

# 设置日志记录
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('auto_updater')

# 全局配置
VERSION_FILE = "version.json"
UPDATE_INFO_FILE = "update_info.json"
TEMP_DIR = os.path.join(tempfile.gettempdir(), "ai_assistant_update")
BACKUP_DIR = os.path.join(tempfile.gettempdir(), "ai_assistant_backup")
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30  # 秒

class AutoUpdater:
    """自动更新器类，用于处理应用程序的自动更新"""
    
    def __init__(self, app_name: str = "松瓷机电AI助手", check_url: str = "", 
                 on_progress: Callable[[float, str], None] = None):
        """
        初始化自动更新器
        
        Args:
            app_name (str, optional): 应用程序名称. 默认为 "松瓷机电AI助手"
            check_url (str, optional): 检查更新的URL. 默认为 ""
            on_progress (Callable[[float, str], None], optional): 更新进度回调函数. 默认为 None
        """
        self.app_name = app_name
        self.check_url = check_url
        self.on_progress = on_progress
        self.version_file = VERSION_FILE
        self.update_info_file = UPDATE_INFO_FILE
        self.temp_dir = TEMP_DIR
        self.backup_dir = BACKUP_DIR
        self.current_version = "0.0.0"
        self.latest_version = "0.0.0"
        self.update_url = ""
        self.update_size = 0
        self.file_updates = []
        self.is_updating = False
        self.update_thread = None
        
        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 加载当前版本信息
        self._load_current_version()
    
    def _load_current_version(self) -> bool:
        """
        加载当前版本信息
        
        Returns:
            bool: 加载是否成功
        """
        if not os.path.exists(self.version_file):
            logger.warning(f"版本文件不存在: {self.version_file}")
            return False
        
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                version_info = json.load(f)
                self.current_version = version_info.get('version', '0.0.0')
                logger.info(f"当前版本: {self.current_version}")
                return True
        except Exception as e:
            logger.error(f"加载版本信息失败: {e}")
            return False
    
    def check_for_updates(self, url: str = "") -> Tuple[bool, str, str]:
        """
        检查是否有可用更新
        
        Args:
            url (str, optional): 检查更新的URL，会覆盖初始化时设置的URL. 默认为 ""
        
        Returns:
            Tuple[bool, str, str]: (是否有更新, 当前版本, 最新版本)
        """
        check_url = url or self.check_url
        if not check_url:
            logger.error("未指定检查更新的URL")
            return False, self.current_version, self.latest_version
        
        logger.info(f"正在检查更新: {check_url}")
        
        try:
            # 发送请求获取更新信息
            response = requests.get(check_url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            
            # 解析更新信息
            update_info = response.json()
            self.latest_version = update_info.get('new_version', '0.0.0')
            self.update_url = update_info.get('update_url', '')
            self.update_size = update_info.get('update_size', 0)
            self.file_updates = update_info.get('file_updates', [])
            required_update = update_info.get('required_update', False)
            
            # 保存更新信息
            with open(self.update_info_file, 'w', encoding='utf-8') as f:
                json.dump(update_info, f, ensure_ascii=False, indent=2)
            
            # 比较版本
            has_update = self._is_newer_version(self.latest_version, self.current_version)
            if has_update:
                logger.info(f"发现新版本: {self.latest_version}")
                if required_update:
                    logger.info("这是一个必须更新的版本")
            else:
                logger.info("当前已是最新版本")
            
            return has_update, self.current_version, self.latest_version
            
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            return False, self.current_version, self.latest_version
    
    def download_updates(self, url: str = "") -> bool:
        """
        下载更新文件
        
        Args:
            url (str, optional): 更新包下载URL，会覆盖检查更新时获取的URL. 默认为 ""
        
        Returns:
            bool: 下载是否成功
        """
        download_url = url or self.update_url
        if not download_url:
            logger.error("未指定更新包下载URL")
            return False
        
        # 如果已经在更新中，则返回
        if self.is_updating:
            logger.warning("已有更新正在进行中")
            return False
        
        # 设置更新状态
        self.is_updating = True
        
        # 清理临时目录
        self._clean_temp_dir()
        
        # 启动更新线程
        self.update_thread = threading.Thread(
            target=self._download_and_update, 
            args=(download_url,)
        )
        self.update_thread.daemon = True
        self.update_thread.start()
        
        return True
    
    def apply_updates(self) -> bool:
        """
        应用已下载的更新
        
        Returns:
            bool: 应用是否成功
        """
        if not os.path.exists(os.path.join(self.temp_dir, "update.zip")):
            logger.error("更新包不存在，请先下载更新")
            return False
        
        try:
            # 解压更新包
            if self._report_progress(0.6, "正在解压更新包..."):
                with zipfile.ZipFile(os.path.join(self.temp_dir, "update.zip"), 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
            
            # 备份当前文件
            if self._report_progress(0.7, "正在备份当前文件..."):
                self._backup_current_files()
            
            # 应用更新
            if self._report_progress(0.8, "正在应用更新..."):
                self._apply_file_updates()
            
            # 更新版本信息
            if self._report_progress(0.9, "正在更新版本信息..."):
                self._update_version_info()
            
            self._report_progress(1.0, "更新完成")
            logger.info(f"已成功更新到版本 {self.latest_version}")
            return True
            
        except Exception as e:
            logger.error(f"应用更新失败: {e}")
            # 发生错误时尝试回滚
            self._rollback_update()
            return False
        finally:
            # 重置更新状态
            self.is_updating = False
    
    def restart_application(self) -> bool:
        """
        重启应用程序
        
        Returns:
            bool: 重启是否成功
        """
        try:
            logger.info("正在重启应用程序...")
            
            # 获取当前执行文件路径
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包的应用
                app_path = sys.executable
            else:
                # 普通 Python 脚本
                app_path = sys.argv[0]
            
            # 使用子进程启动应用，然后退出当前进程
            subprocess.Popen([app_path])
            
            # 退出当前进程
            os._exit(0)
            
            return True
        except Exception as e:
            logger.error(f"重启应用程序失败: {e}")
            return False
    
    def _download_and_update(self, url: str) -> None:
        """
        下载并应用更新的内部方法
        
        Args:
            url (str): 更新包下载URL
        """
        try:
            # 下载更新包
            download_path = os.path.join(self.temp_dir, "update.zip")
            self._report_progress(0.1, "开始下载更新...")
            
            # 下载文件
            response = requests.get(url, stream=True, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 写入文件
            with open(download_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = min(0.5, 0.1 + (downloaded / total_size) * 0.4)
                        self._report_progress(progress, f"下载中... {downloaded/1024/1024:.1f}/{total_size/1024/1024:.1f} MB")
            
            self._report_progress(0.5, "下载完成")
            
            # 应用更新
            self.apply_updates()
            
        except Exception as e:
            logger.error(f"下载更新失败: {e}")
            self._report_progress(0, f"更新失败: {str(e)}")
            self.is_updating = False
    
    def _backup_current_files(self) -> None:
        """备份当前文件"""
        # 清理备份目录
        if os.path.exists(self.backup_dir):
            shutil.rmtree(self.backup_dir)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 加载更新信息
        with open(self.update_info_file, 'r', encoding='utf-8') as f:
            update_info = json.load(f)
        file_updates = update_info.get('file_updates', [])
        
        # 备份将要更新的文件
        for file_update in file_updates:
            file_path = file_update['path']
            if file_update['action'] in ['update', 'delete'] and os.path.exists(file_path):
                # 创建目录结构
                backup_file_path = os.path.join(self.backup_dir, file_path)
                os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                
                # 复制文件
                shutil.copy2(file_path, backup_file_path)
                logger.info(f"已备份文件: {file_path}")
    
    def _apply_file_updates(self) -> None:
        """应用文件更新"""
        # 加载更新信息
        with open(self.update_info_file, 'r', encoding='utf-8') as f:
            update_info = json.load(f)
        file_updates = update_info.get('file_updates', [])
        
        # 应用更新
        for file_update in file_updates:
            path = file_update['path']
            action = file_update['action']
            
            if action == 'add' or action == 'update':
                # 创建目录结构
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                # 从临时目录复制新文件
                temp_file_path = os.path.join(self.temp_dir, path)
                if os.path.exists(temp_file_path):
                    # 如果目标文件存在且无法覆盖，先删除它
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            # 如果无法删除，可能是文件正在使用
                            logger.warning(f"无法删除文件: {path}，将在下次启动时更新")
                            continue
                    
                    # 复制新文件
                    shutil.copy2(temp_file_path, path)
                    logger.info(f"已更新文件: {path}")
            
            elif action == 'delete':
                # 删除文件
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info(f"已删除文件: {path}")
                    except:
                        logger.warning(f"无法删除文件: {path}，将在下次启动时删除")
    
    def _update_version_info(self) -> None:
        """更新版本信息文件"""
        # 更新version.json
        if os.path.exists(os.path.join(self.temp_dir, VERSION_FILE)):
            shutil.copy2(os.path.join(self.temp_dir, VERSION_FILE), VERSION_FILE)
        
        # 或者直接更新版本号
        elif os.path.exists(VERSION_FILE):
            try:
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    version_info = json.load(f)
                
                version_info['version'] = self.latest_version
                version_info['build_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                version_info['build_timestamp'] = int(time.time())
                
                with open(VERSION_FILE, 'w', encoding='utf-8') as f:
                    json.dump(version_info, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"更新版本信息失败: {e}")
    
    def _rollback_update(self) -> None:
        """回滚更新"""
        logger.info("正在回滚更新...")
        
        try:
            # 遍历备份目录
            for root, dirs, files in os.walk(self.backup_dir):
                for file in files:
                    backup_path = os.path.join(root, file)
                    relative_path = os.path.relpath(backup_path, self.backup_dir)
                    target_path = os.path.abspath(relative_path)
                    
                    # 恢复文件
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(backup_path, target_path)
                    logger.info(f"已恢复文件: {relative_path}")
            
            logger.info("回滚完成")
        except Exception as e:
            logger.error(f"回滚更新失败: {e}")
    
    def _clean_temp_dir(self) -> None:
        """清理临时目录"""
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                os.makedirs(self.temp_dir, exist_ok=True)
                logger.info("已清理临时目录")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """
        检查version1是否高于version2
        
        Args:
            version1 (str): 第一个版本号
            version2 (str): 第二个版本号
        
        Returns:
            bool: version1是否高于version2
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(min(len(v1_parts), len(v2_parts))):
            if v1_parts[i] > v2_parts[i]:
                return True
            elif v1_parts[i] < v2_parts[i]:
                return False
        
        # 如果前面的部分都相等，则比较长度
        return len(v1_parts) > len(v2_parts)
    
    def _report_progress(self, progress: float, message: str) -> bool:
        """
        报告更新进度
        
        Args:
            progress (float): 进度百分比 (0-1)
            message (str): 进度消息
        
        Returns:
            bool: 是否应该继续更新
        """
        # 记录日志
        logger.info(f"更新进度: {progress:.1%} - {message}")
        
        # 如果有回调函数，则调用它
        if self.on_progress:
            try:
                self.on_progress(progress, message)
            except Exception as e:
                logger.warning(f"调用进度回调函数失败: {e}")
        
        # 检查是否应该继续更新
        return self.is_updating


def create_updater_ui():
    """创建一个简单的更新器UI界面"""
    try:
        import tkinter as tk
        from tkinter import ttk
        from tkinter import messagebox
    except ImportError:
        logger.error("无法导入tkinter，无法创建更新器UI界面")
        return
    
    class UpdaterUI:
        def __init__(self, root, check_url):
            self.root = root
            self.check_url = check_url
            self.setup_ui()
            self.updater = AutoUpdater(check_url=check_url, on_progress=self.update_progress)
            
            # 自动检查更新
            self.root.after(1000, self.check_for_updates)
        
        def setup_ui(self):
            self.root.title("松瓷机电AI助手更新器")
            self.root.geometry("400x250")
            self.root.resizable(False, False)
            
            # 设置样式
            style = ttk.Style()
            style.configure("TButton", padding=6, relief="flat", background="#ccc")
            
            # 创建控件
            main_frame = ttk.Frame(self.root, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题标签
            title_label = ttk.Label(main_frame, text="松瓷机电AI助手更新", font=("Helvetica", 16))
            title_label.pack(pady=10)
            
            # 版本信息
            self.version_frame = ttk.Frame(main_frame)
            self.version_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(self.version_frame, text="当前版本: ").grid(row=0, column=0, sticky=tk.W)
            self.current_version_label = ttk.Label(self.version_frame, text="检查中...")
            self.current_version_label.grid(row=0, column=1, sticky=tk.W)
            
            ttk.Label(self.version_frame, text="最新版本: ").grid(row=1, column=0, sticky=tk.W)
            self.latest_version_label = ttk.Label(self.version_frame, text="检查中...")
            self.latest_version_label.grid(row=1, column=1, sticky=tk.W)
            
            # 进度条
            self.progress_frame = ttk.Frame(main_frame)
            self.progress_frame.pack(fill=tk.X, pady=10)
            
            self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, length=380, mode='determinate')
            self.progress_bar.pack(fill=tk.X)
            
            self.status_label = ttk.Label(self.progress_frame, text="准备检查更新...")
            self.status_label.pack(anchor=tk.W, pady=5)
            
            # 按钮
            self.button_frame = ttk.Frame(main_frame)
            self.button_frame.pack(fill=tk.X, pady=10)
            
            self.check_button = ttk.Button(self.button_frame, text="检查更新", command=self.check_for_updates)
            self.check_button.pack(side=tk.LEFT, padx=5)
            
            self.update_button = ttk.Button(self.button_frame, text="更新", command=self.download_and_update, state=tk.DISABLED)
            self.update_button.pack(side=tk.LEFT, padx=5)
            
            self.restart_button = ttk.Button(self.button_frame, text="重启应用", command=self.restart_app, state=tk.DISABLED)
            self.restart_button.pack(side=tk.LEFT, padx=5)
            
            self.exit_button = ttk.Button(self.button_frame, text="退出", command=self.root.destroy)
            self.exit_button.pack(side=tk.RIGHT, padx=5)
        
        def check_for_updates(self):
            self.status_label.config(text="正在检查更新...")
            self.progress_bar['value'] = 10
            
            # 在后台线程中检查更新
            def check_thread():
                has_update, current_version, latest_version = self.updater.check_for_updates()
                
                # 在主线程更新UI
                self.root.after(0, lambda: self.update_version_info(has_update, current_version, latest_version))
            
            # 启动线程
            threading.Thread(target=check_thread, daemon=True).start()
        
        def update_version_info(self, has_update, current_version, latest_version):
            self.current_version_label.config(text=current_version)
            self.latest_version_label.config(text=latest_version)
            
            if has_update:
                self.status_label.config(text=f"发现新版本: {latest_version}")
                self.update_button.config(state=tk.NORMAL)
                self.progress_bar['value'] = 0
                
                # 询问是否更新
                if messagebox.askyesno("更新可用", f"发现新版本: {latest_version}\n是否立即更新?"):
                    self.download_and_update()
            else:
                self.status_label.config(text="当前已是最新版本")
                self.progress_bar['value'] = 100
                self.update_button.config(state=tk.DISABLED)
        
        def download_and_update(self):
            self.check_button.config(state=tk.DISABLED)
            self.update_button.config(state=tk.DISABLED)
            self.exit_button.config(state=tk.DISABLED)
            
            # 开始下载更新
            self.updater.download_updates()
        
        def update_progress(self, progress, message):
            self.progress_bar['value'] = progress * 100
            self.status_label.config(text=message)
            
            # 如果更新完成，启用重启按钮
            if progress >= 1.0:
                self.restart_button.config(state=tk.NORMAL)
                self.exit_button.config(state=tk.NORMAL)
                messagebox.showinfo("更新完成", "应用程序已更新完成，请重启应用以应用更新。")
        
        def restart_app(self):
            self.updater.restart_application()
    
    # 创建并运行UI
    root = tk.Tk()
    app = UpdaterUI(root, check_url="https://example.com/updates.json")  # 替换为实际的更新检查URL
    root.mainloop()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="松瓷机电AI助手程序自动更新工具")
    parser.add_argument("--check", action="store_true", help="检查更新")
    parser.add_argument("--url", type=str, help="更新服务器URL")
    parser.add_argument("--download", action="store_true", help="下载并应用更新")
    parser.add_argument("--restart", action="store_true", help="应用更新后重启应用")
    parser.add_argument("--gui", action="store_true", help="启动图形界面")
    
    args = parser.parse_args()
    
    # 如果没有参数，或者指定了GUI参数，则启动图形界面
    if len(sys.argv) == 1 or args.gui:
        create_updater_ui()
        return 0
    
    # 创建更新器
    updater = AutoUpdater(check_url=args.url)
    
    # 检查更新
    if args.check:
        has_update, current_version, latest_version = updater.check_for_updates(args.url)
        if has_update:
            print(f"发现新版本: {latest_version} (当前版本: {current_version})")
            
            # 如果指定了下载参数，则下载并应用更新
            if args.download:
                print("开始下载更新...")
                updater.download_updates()
                
                # 等待下载完成
                while updater.is_updating:
                    time.sleep(0.5)
                
                print("更新完成")
                
                # 如果指定了重启参数，则重启应用
                if args.restart:
                    updater.restart_application()
        else:
            print(f"当前已是最新版本: {current_version}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 