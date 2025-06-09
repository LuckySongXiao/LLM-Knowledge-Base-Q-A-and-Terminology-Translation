#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
version_manager.py - 松瓷机电AI助手程序版本管理工具

此脚本用于管理松瓷机电AI助手程序的版本信息，生成版本更新文件，
并提供版本比较功能，支持自动升级。
"""

import os
import sys
import json
import time
import logging
import hashlib
import argparse
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

# 设置日志记录
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('version_manager')

# 全局配置
VERSION_FILE = "version.json"
UPDATE_INFO_FILE = "update_info.json"
CHANGELOG_FILE = "CHANGELOG.md"
PACKAGE_DIR = "packages"

class VersionManager:
    """版本管理器类，用于处理应用程序版本信息"""
    
    def __init__(self, app_name: str, app_version: str = "1.0.0"):
        """
        初始化版本管理器
        
        Args:
            app_name (str): 应用程序名称
            app_version (str, optional): 应用程序版本. 默认为 "1.0.0"
        """
        self.app_name = app_name
        self.version = app_version
        self.version_file = VERSION_FILE
        self.update_info_file = UPDATE_INFO_FILE
        self.changelog_file = CHANGELOG_FILE
        self.package_dir = PACKAGE_DIR
        
        # 版本信息字典
        self.version_info = {
            "name": app_name,
            "version": app_version,
            "build_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "build_timestamp": int(time.time()),
            "files": [],
            "release_notes": "",
            "required_update": False,
            "update_url": "",
            "check_url": ""
        }
        
        # 如果版本文件存在，则加载它
        if os.path.exists(self.version_file):
            self.load_version_info()
        else:
            # 否则，创建新的版本文件
            self.save_version_info()
            logger.info(f"已创建新的版本文件: {self.version_file}")
    
    def load_version_info(self) -> bool:
        """
        从文件加载版本信息
        
        Returns:
            bool: 加载是否成功
        """
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                self.version_info = json.load(f)
                logger.info(f"已加载版本信息: {self.version_info['version']}")
                return True
        except Exception as e:
            logger.error(f"加载版本信息失败: {e}")
            return False
    
    def save_version_info(self) -> bool:
        """
        保存版本信息到文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(self.version_info, f, ensure_ascii=False, indent=2)
                logger.info(f"已保存版本信息: {self.version_info['version']}")
                return True
        except Exception as e:
            logger.error(f"保存版本信息失败: {e}")
            return False
    
    def update_version(self, new_version: str, release_notes: str = "") -> bool:
        """
        更新应用程序版本
        
        Args:
            new_version (str): 新的版本号
            release_notes (str, optional): 版本更新说明. 默认为 ""
        
        Returns:
            bool: 更新是否成功
        """
        # 检查版本格式
        if not self._validate_version_format(new_version):
            logger.error(f"无效的版本格式: {new_version}")
            return False
        
        # 检查是否是更高版本
        if not self._is_higher_version(new_version):
            logger.warning(f"新版本 {new_version} 不高于当前版本 {self.version_info['version']}")
            return False
        
        # 更新版本信息
        old_version = self.version_info['version']
        self.version_info['version'] = new_version
        self.version_info['build_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.version_info['build_timestamp'] = int(time.time())
        
        # 更新发布说明
        if release_notes:
            self.version_info['release_notes'] = release_notes
            # 同时更新变更日志
            self._update_changelog(old_version, new_version, release_notes)
        
        # 保存更新后的版本信息
        if self.save_version_info():
            logger.info(f"版本已从 {old_version} 更新到 {new_version}")
            return True
        return False
    
    def scan_files(self, directory: str, patterns: List[str] = None) -> bool:
        """
        扫描指定目录中的文件，并更新文件信息
        
        Args:
            directory (str): 要扫描的目录路径
            patterns (List[str], optional): 要包含的文件模式列表. 默认为 None (包含所有文件)
        
        Returns:
            bool: 扫描是否成功
        """
        if not os.path.exists(directory):
            logger.error(f"目录不存在: {directory}")
            return False
        
        logger.info(f"开始扫描目录: {directory}")
        
        # 重置文件列表
        self.version_info['files'] = []
        file_count = 0
        
        # 遍历目录
        for root, _, files in os.walk(directory):
            for filename in files:
                if patterns and not self._match_patterns(filename, patterns):
                    continue
                
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, directory)
                
                # 计算文件哈希值
                file_hash = self._calculate_file_hash(file_path)
                if file_hash:
                    file_size = os.path.getsize(file_path)
                    file_info = {
                        "path": rel_path,
                        "hash": file_hash,
                        "size": file_size
                    }
                    self.version_info['files'].append(file_info)
                    file_count += 1
        
        logger.info(f"已扫描 {file_count} 个文件")
        return self.save_version_info()
    
    def generate_update_info(self, old_version_file: str, update_url: str = "") -> bool:
        """
        生成更新信息文件，用于应用程序自动更新
        
        Args:
            old_version_file (str): 旧版本信息文件的路径
            update_url (str, optional): 更新包下载URL. 默认为 ""
        
        Returns:
            bool: 是否成功生成更新信息
        """
        if not os.path.exists(old_version_file):
            logger.error(f"旧版本文件不存在: {old_version_file}")
            return False
        
        # 加载旧版本信息
        try:
            with open(old_version_file, 'r', encoding='utf-8') as f:
                old_version_info = json.load(f)
        except Exception as e:
            logger.error(f"加载旧版本信息失败: {e}")
            return False
        
        # 比较版本
        old_version = old_version_info.get('version', '0.0.0')
        new_version = self.version_info.get('version', '1.0.0')
        
        if not self._is_higher_version(new_version, old_version):
            logger.warning(f"当前版本 {new_version} 不高于旧版本 {old_version}")
            return False
        
        # 构建更新信息
        update_info = {
            "app_name": self.app_name,
            "old_version": old_version,
            "new_version": new_version,
            "update_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "update_timestamp": int(time.time()),
            "update_url": update_url or self.version_info.get('update_url', ''),
            "check_url": self.version_info.get('check_url', ''),
            "release_notes": self.version_info.get('release_notes', ''),
            "required_update": self.version_info.get('required_update', False),
            "file_updates": []
        }
        
        # 计算需要更新的文件
        old_files = {f['path']: f for f in old_version_info.get('files', [])}
        new_files = {f['path']: f for f in self.version_info.get('files', [])}
        
        # 查找已修改和新增的文件
        update_size = 0
        for path, new_file in new_files.items():
            if path in old_files:
                # 文件存在于旧版本，检查哈希值是否变化
                if new_file['hash'] != old_files[path]['hash']:
                    file_update = {
                        "path": path,
                        "action": "update",
                        "size": new_file['size']
                    }
                    update_info['file_updates'].append(file_update)
                    update_size += new_file['size']
            else:
                # 新文件
                file_update = {
                    "path": path,
                    "action": "add",
                    "size": new_file['size']
                }
                update_info['file_updates'].append(file_update)
                update_size += new_file['size']
        
        # 查找已删除的文件
        for path in old_files:
            if path not in new_files:
                file_update = {
                    "path": path,
                    "action": "delete",
                    "size": 0
                }
                update_info['file_updates'].append(file_update)
        
        # 添加总更新大小
        update_info['update_size'] = update_size
        
        # 保存更新信息
        try:
            with open(self.update_info_file, 'w', encoding='utf-8') as f:
                json.dump(update_info, f, ensure_ascii=False, indent=2)
            logger.info(f"已生成更新信息文件: {self.update_info_file}")
            logger.info(f"更新文件数: {len(update_info['file_updates'])}, 总大小: {update_size} 字节")
            return True
        except Exception as e:
            logger.error(f"保存更新信息失败: {e}")
            return False
    
    def create_update_package(self, old_version_file: str, output_dir: str = None) -> str:
        """
        创建更新包
        
        Args:
            old_version_file (str): 旧版本信息文件的路径
            output_dir (str, optional): 输出目录. 默认为当前目录下的packages子目录
        
        Returns:
            str: 更新包文件路径，失败则返回空字符串
        """
        import zipfile
        
        # 先生成更新信息
        if not self.generate_update_info(old_version_file):
            logger.error("生成更新信息失败，无法创建更新包")
            return ""
        
        # 确保输出目录存在
        if output_dir is None:
            output_dir = self.package_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载更新信息
        with open(self.update_info_file, 'r', encoding='utf-8') as f:
            update_info = json.load(f)
        
        # 创建更新包文件名
        old_version = update_info['old_version']
        new_version = update_info['new_version']
        update_package_name = f"{self.app_name}_update_{old_version}_to_{new_version}.zip"
        update_package_path = os.path.join(output_dir, update_package_name)
        
        # 创建更新包
        try:
            with zipfile.ZipFile(update_package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加更新信息文件
                zipf.write(self.update_info_file, os.path.basename(self.update_info_file))
                
                # 添加版本信息文件
                zipf.write(self.version_file, os.path.basename(self.version_file))
                
                # 添加需要更新的文件
                for file_update in update_info['file_updates']:
                    if file_update['action'] in ['add', 'update']:
                        file_path = file_update['path']
                        if os.path.exists(file_path):
                            zipf.write(file_path, file_path)
                        else:
                            logger.warning(f"文件不存在: {file_path}")
            
            logger.info(f"已创建更新包: {update_package_path}")
            return update_package_path
        except Exception as e:
            logger.error(f"创建更新包失败: {e}")
            return ""
    
    def set_required_update(self, required: bool = True) -> bool:
        """
        设置是否为必须更新
        
        Args:
            required (bool, optional): 是否为必须更新. 默认为 True
        
        Returns:
            bool: 设置是否成功
        """
        self.version_info['required_update'] = required
        return self.save_version_info()
    
    def set_update_url(self, url: str) -> bool:
        """
        设置更新包下载URL
        
        Args:
            url (str): 更新包下载URL
        
        Returns:
            bool: 设置是否成功
        """
        self.version_info['update_url'] = url
        return self.save_version_info()
    
    def set_check_url(self, url: str) -> bool:
        """
        设置检查更新的URL
        
        Args:
            url (str): 检查更新的URL
        
        Returns:
            bool: 设置是否成功
        """
        self.version_info['check_url'] = url
        return self.save_version_info()
    
    def _validate_version_format(self, version: str) -> bool:
        """
        验证版本号格式是否有效
        
        Args:
            version (str): 版本号
        
        Returns:
            bool: 格式是否有效
        """
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    def _is_higher_version(self, version1: str, version2: str = None) -> bool:
        """
        检查version1是否高于version2
        
        Args:
            version1 (str): 第一个版本号
            version2 (str, optional): 第二个版本号. 默认为当前版本
        
        Returns:
            bool: version1是否高于version2
        """
        if version2 is None:
            version2 = self.version_info['version']
        
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(min(len(v1_parts), len(v2_parts))):
            if v1_parts[i] > v2_parts[i]:
                return True
            elif v1_parts[i] < v2_parts[i]:
                return False
        
        # 如果前面的部分都相等，则比较长度
        return len(v1_parts) > len(v2_parts)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        计算文件的SHA256哈希值
        
        Args:
            file_path (str): 文件路径
        
        Returns:
            str: 哈希值，如果计算失败则返回空字符串
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # 读取文件块并更新哈希
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"计算文件 {file_path} 哈希值失败: {e}")
            return ""
    
    def _match_patterns(self, filename: str, patterns: List[str]) -> bool:
        """
        检查文件名是否匹配模式列表中的任何一个模式
        
        Args:
            filename (str): 文件名
            patterns (List[str]): 模式列表
        
        Returns:
            bool: 是否匹配
        """
        import fnmatch
        return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)
    
    def _update_changelog(self, old_version: str, new_version: str, release_notes: str) -> None:
        """
        更新变更日志文件
        
        Args:
            old_version (str): 旧版本号
            new_version (str): 新版本号
            release_notes (str): 版本更新说明
        """
        # 获取当前日期
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 创建新的变更日志条目
        changelog_entry = f"""## {new_version} ({today})

{release_notes}

"""
        
        # 如果文件存在，则将新条目添加到开头
        if os.path.exists(self.changelog_file):
            with open(self.changelog_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        else:
            # 创建新的变更日志文件，添加标题
            existing_content = f"# 变更日志\n\n"
        
        # 写入更新后的变更日志
        with open(self.changelog_file, 'w', encoding='utf-8') as f:
            # 检查是否已经有标题，确保只保留一个标题
            if existing_content.startswith("# 变更日志"):
                # 已有标题，在标题之后添加新条目
                title_end = existing_content.find('\n\n')
                if title_end != -1:
                    f.write(existing_content[:title_end+2] + changelog_entry + existing_content[title_end+2:])
                else:
                    f.write(existing_content + '\n' + changelog_entry)
            else:
                # 没有标题，添加标题和新条目
                f.write(f"# 变更日志\n\n{changelog_entry}{existing_content}")
        
        logger.info(f"已更新变更日志: {self.changelog_file}")

    def publish_update(self, server_url: str, package_path: str = None, api_key: str = None) -> bool:
        """
        发布更新到服务器
        
        Args:
            server_url (str): 服务器URL
            package_path (str, optional): 更新包路径. 默认为None（自动选择最新创建的更新包）
            api_key (str, optional): API密钥. 默认为None
        
        Returns:
            bool: 发布是否成功
        """
        try:
            import requests
            
            # 如果未指定更新包，找到最新创建的更新包
            if not package_path:
                if not os.path.exists(self.package_dir):
                    logger.error(f"更新包目录不存在: {self.package_dir}")
                    return False
                
                # 找到最新的更新包
                packages = []
                for file in os.listdir(self.package_dir):
                    if file.startswith(f"{self.app_name}_update_") and file.endswith(".zip"):
                        file_path = os.path.join(self.package_dir, file)
                        packages.append((file_path, os.path.getmtime(file_path)))
                
                if not packages:
                    logger.error("未找到更新包")
                    return False
                
                # 按修改时间排序，选择最新的
                packages.sort(key=lambda x: x[1], reverse=True)
                package_path = packages[0][0]
            
            if not os.path.exists(package_path):
                logger.error(f"更新包不存在: {package_path}")
                return False
            
            # 构建请求数据
            files = {'package': open(package_path, 'rb')}
            data = {
                'app_name': self.app_name,
                'version': self.version_info['version'],
                'release_notes': self.version_info['release_notes'],
                'required_update': 'true' if self.version_info['required_update'] else 'false'
            }
            
            # 添加API密钥（如果有）
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            # 发送请求
            response = requests.post(f"{server_url}/api/updates/publish", 
                                    files=files, 
                                    data=data, 
                                    headers=headers)
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                
                # 更新URL
                if 'update_url' in result:
                    self.set_update_url(result['update_url'])
                
                if 'check_url' in result:
                    self.set_check_url(result['check_url'])
                
                logger.info(f"更新已成功发布: {result.get('message', '成功')}")
                return True
            else:
                logger.error(f"发布更新失败: HTTP {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"发布更新时出错: {e}")
            return False

def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="松瓷机电AI助手程序版本管理工具")
    
    # 基本参数
    parser.add_argument("--name", type=str, default="松瓷机电AI助手", help="应用程序名称")
    parser.add_argument("--version", type=str, help="应用程序版本号 (例如: 1.0.0)")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 创建/更新版本信息命令
    update_parser = subparsers.add_parser("update", help="更新版本信息")
    update_parser.add_argument("new_version", type=str, help="新版本号 (例如: 1.0.1)")
    update_parser.add_argument("--notes", type=str, help="版本更新说明")
    update_parser.add_argument("--required", action="store_true", help="是否为必须更新")
    update_parser.add_argument("--url", type=str, help="更新包下载URL")
    update_parser.add_argument("--check-url", type=str, help="检查更新的URL")
    
    # 扫描文件命令
    scan_parser = subparsers.add_parser("scan", help="扫描文件并更新版本信息")
    scan_parser.add_argument("directory", type=str, help="要扫描的目录路径")
    scan_parser.add_argument("--patterns", type=str, nargs="*", help="要包含的文件模式 (例如: *.exe *.dll)")
    
    # 生成更新信息命令
    generate_parser = subparsers.add_parser("generate", help="生成更新信息文件")
    generate_parser.add_argument("old_version_file", type=str, help="旧版本信息文件的路径")
    generate_parser.add_argument("--url", type=str, help="更新包下载URL")
    
    # 创建更新包命令
    package_parser = subparsers.add_parser("package", help="创建更新包")
    package_parser.add_argument("old_version_file", type=str, help="旧版本信息文件的路径")
    package_parser.add_argument("--output", type=str, help="输出目录")
    
    # 发布更新命令
    publish_parser = subparsers.add_parser("publish", help="发布更新到服务器")
    publish_parser.add_argument("server_url", type=str, help="服务器URL")
    publish_parser.add_argument("--package", type=str, help="更新包路径")
    publish_parser.add_argument("--api-key", type=str, help="API密钥")
    
    # 显示版本信息命令
    subparsers.add_parser("show", help="显示当前版本信息")
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    # 初始化版本管理器
    version_manager = VersionManager(args.name, args.version)
    
    # 执行命令
    if args.command == "update":
        # 更新版本
        success = version_manager.update_version(args.new_version, args.notes or "")
        
        # 设置必须更新标志
        if success and args.required:
            version_manager.set_required_update(True)
        
        # 设置更新URL
        if success and args.url:
            version_manager.set_update_url(args.url)
        
        # 设置检查URL
        if success and args.check_url:
            version_manager.set_check_url(args.check_url)
        
        return 0 if success else 1
    
    elif args.command == "scan":
        # 扫描文件
        success = version_manager.scan_files(args.directory, args.patterns)
        return 0 if success else 1
    
    elif args.command == "generate":
        # 生成更新信息
        success = version_manager.generate_update_info(args.old_version_file, args.url or "")
        return 0 if success else 1
    
    elif args.command == "package":
        # 创建更新包
        package_path = version_manager.create_update_package(args.old_version_file, args.output)
        return 0 if package_path else 1
        
    elif args.command == "publish":
        # 发布更新
        success = version_manager.publish_update(args.server_url, args.package, args.api_key)
        return 0 if success else 1
    
    elif args.command == "show":
        # 显示版本信息
        print(json.dumps(version_manager.version_info, ensure_ascii=False, indent=2))
        return 0
    
    else:
        # 没有指定命令，显示帮助信息
        logger.error("请指定要执行的命令")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 