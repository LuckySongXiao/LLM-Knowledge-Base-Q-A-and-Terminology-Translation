#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_auto_updater.py - 自动更新器测试脚本

此脚本用于测试自动更新器的功能。
支持模拟更新服务器响应和更新过程。
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# 导入自动更新器
from auto_updater import AutoUpdater

# 测试配置
TEST_SERVER_PORT = 8000
TEST_SERVER_URL = f"http://localhost:{TEST_SERVER_PORT}"
TEST_CHECK_URL = f"{TEST_SERVER_URL}/updates.json"
TEST_DOWNLOAD_URL = f"{TEST_SERVER_URL}/download/update.zip"
TEST_APP_NAME = "测试应用"
TEST_CURRENT_VERSION = "1.0.0"
TEST_NEW_VERSION = "1.0.1"

class MockHTTPRequestHandler(BaseHTTPRequestHandler):
    """模拟HTTP请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == "/updates.json":
            self._serve_update_info()
        elif self.path.startswith("/download/"):
            self._serve_update_package()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
    
    def _serve_update_info(self):
        """提供更新信息"""
        update_info = {
            "app_name": TEST_APP_NAME,
            "old_version": TEST_CURRENT_VERSION,
            "new_version": TEST_NEW_VERSION,
            "update_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_timestamp": int(time.time()),
            "update_url": TEST_DOWNLOAD_URL,
            "check_url": TEST_CHECK_URL,
            "release_notes": "这是一个测试更新，用于测试自动更新器功能。",
            "required_update": False,
            "update_size": 1024,
            "file_updates": [
                {
                    "path": "test_file.txt",
                    "action": "update",
                    "size": 1024
                }
            ]
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(update_info).encode())
    
    def _serve_update_package(self):
        """提供更新包"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 创建测试文件
            with open(os.path.join(temp_dir, "test_file.txt"), "w") as f:
                f.write("这是更新后的测试文件。")
            
            # 创建更新信息文件
            update_info = {
                "app_name": TEST_APP_NAME,
                "version": TEST_NEW_VERSION,
                "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "build_timestamp": int(time.time()),
                "files": [
                    {
                        "path": "test_file.txt",
                        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "size": 1024
                    }
                ]
            }
            
            with open(os.path.join(temp_dir, "version.json"), "w") as f:
                json.dump(update_info, f)
            
            # 创建更新包
            import zipfile
            zip_path = os.path.join(temp_dir, "update.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                zipf.write(os.path.join(temp_dir, "test_file.txt"), "test_file.txt")
                zipf.write(os.path.join(temp_dir, "version.json"), "version.json")
            
            # 读取更新包
            with open(zip_path, "rb") as f:
                update_data = f.read()
            
            # 返回更新包
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(update_data)))
            self.end_headers()
            self.wfile.write(update_data)
        
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir)


class TestAutoUpdater(unittest.TestCase):
    """自动更新器测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 启动模拟服务器
        cls.httpd = HTTPServer(("localhost", TEST_SERVER_PORT), MockHTTPRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
    
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        # 关闭模拟服务器
        cls.httpd.shutdown()
        cls.server_thread.join()
    
    def setUp(self):
        """每个测试前的设置"""
        # 设置测试目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        self.test_file_path = os.path.join(self.test_dir, "test_file.txt")
        with open(self.test_file_path, "w") as f:
            f.write("这是原始测试文件。")
        
        # 创建版本信息文件
        self.version_file_path = os.path.join(self.test_dir, "version.json")
        with open(self.version_file_path, "w") as f:
            json.dump({
                "name": TEST_APP_NAME,
                "version": TEST_CURRENT_VERSION,
                "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "build_timestamp": int(time.time()),
                "files": []
            }, f)
        
        # 切换到测试目录
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # 创建自动更新器
        self.progress_messages = []
        self.updater = AutoUpdater(
            app_name=TEST_APP_NAME,
            check_url=TEST_CHECK_URL,
            on_progress=self._progress_callback
        )
    
    def tearDown(self):
        """每个测试后的清理"""
        # 切换回原始目录
        os.chdir(self.old_cwd)
        
        # 清理测试目录
        shutil.rmtree(self.test_dir)
    
    def _progress_callback(self, progress, message):
        """进度回调函数"""
        self.progress_messages.append((progress, message))
    
    def test_check_for_updates(self):
        """测试检查更新功能"""
        # 检查更新
        has_update, current_version, latest_version = self.updater.check_for_updates()
        
        # 验证结果
        self.assertTrue(has_update)
        self.assertEqual(current_version, TEST_CURRENT_VERSION)
        self.assertEqual(latest_version, TEST_NEW_VERSION)
    
    def test_download_and_apply_updates(self):
        """测试下载和应用更新功能"""
        # 检查更新
        has_update, _, _ = self.updater.check_for_updates()
        self.assertTrue(has_update)
        
        # 下载更新
        self.updater.download_updates()
        
        # 等待下载完成
        timeout = 10
        while self.updater.is_updating and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5
        
        # 验证进度消息
        self.assertGreater(len(self.progress_messages), 0)
        self.assertEqual(self.progress_messages[-1][0], 1.0)  # 最后一个进度为100%
        
        # 验证文件已更新
        with open(self.test_file_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "这是更新后的测试文件。")
        
        # 验证版本已更新
        with open(self.version_file_path, "r") as f:
            version_info = json.load(f)
        self.assertEqual(version_info.get("version"), TEST_NEW_VERSION)
    
    def test_backup_and_rollback(self):
        """测试备份和回滚功能"""
        # 检查更新
        self.updater.check_for_updates()
        
        # 手动触发备份
        self.updater._backup_current_files()
        
        # 验证备份目录存在
        self.assertTrue(os.path.exists(self.updater.backup_dir))
        
        # 验证文件已备份
        backup_file_path = os.path.join(self.updater.backup_dir, "test_file.txt")
        self.assertTrue(os.path.exists(backup_file_path))
        
        # 修改原始文件
        with open(self.test_file_path, "w") as f:
            f.write("这是修改后的文件。")
        
        # 触发回滚
        self.updater._rollback_update()
        
        # 验证文件已回滚
        with open(self.test_file_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "这是原始测试文件。")


def main():
    """主函数"""
    unittest.main()


if __name__ == "__main__":
    main() 