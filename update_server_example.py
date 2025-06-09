#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
update_server_example.py - 简单的更新服务器示例

此脚本提供一个简单的HTTP服务器，用于提供更新信息和更新包的下载服务。
这是一个演示示例，仅用于本地测试和开发环境。
生产环境应使用专业的Web服务器和CDN。
"""

import os
import sys
import json
import time
import argparse
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 设置默认端口
DEFAULT_PORT = 8000

# 设置默认目录
DEFAULT_DIR = "packages"

# 全局变量
UPDATE_INFO = None
SERVER_PORT = DEFAULT_PORT
SERVER_DIR = DEFAULT_DIR

class UpdateServerHandler(BaseHTTPRequestHandler):
    """更新服务器请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # 路由处理
        if path == "/":
            self._serve_index()
        elif path == "/updates.json":
            self._serve_update_info()
        elif path == "/api/check":
            self._serve_check_api(parse_qs(parsed_url.query))
        elif path.startswith("/download/"):
            self._serve_file(path[10:])  # 去掉"/download/"前缀
        else:
            self._serve_file(path[1:])  # 去掉"/"前缀
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == "/api/updates/publish":
            self._handle_publish()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
    
    def _serve_index(self):
        """提供首页"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>松瓷机电AI助手更新服务器</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        h1 {{ color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .card {{ background: #f5f5f5; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
        .info {{ display: flex; justify-content: space-between; }}
        .info div {{ flex: 1; }}
        .version {{ font-weight: bold; }}
        .files {{ margin-top: 20px; }}
        .file {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #ddd; }}
        .file:last-child {{ border-bottom: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>松瓷机电AI助手更新服务器</h1>
        
        <div class="card">
            <h2>当前版本信息</h2>
            <div class="info">
                <div>
                    <p><strong>应用名称:</strong> {UPDATE_INFO.get('app_name', '未知')}</p>
                    <p><strong>最新版本:</strong> <span class="version">{UPDATE_INFO.get('new_version', '未知')}</span></p>
                    <p><strong>发布日期:</strong> {UPDATE_INFO.get('update_date', '未知')}</p>
                </div>
                <div>
                    <p><strong>更新大小:</strong> {UPDATE_INFO.get('update_size', 0) / 1024 / 1024:.2f} MB</p>
                    <p><strong>强制更新:</strong> {'是' if UPDATE_INFO.get('required_update', False) else '否'}</p>
                    <p><strong>文件数量:</strong> {len(UPDATE_INFO.get('file_updates', []))}</p>
                </div>
            </div>
            
            <div class="files">
                <h3>更新文件列表</h3>
                {self._generate_file_list_html()}
            </div>
        </div>
        
        <div class="card">
            <h2>API接口</h2>
            <p><strong>检查更新:</strong> <a href="/updates.json" target="_blank">/updates.json</a></p>
            <p><strong>版本检查API:</strong> <a href="/api/check?version=1.0.0" target="_blank">/api/check?version=1.0.0</a></p>
            <p><strong>下载更新包:</strong> <a href="{UPDATE_INFO.get('update_url', '#')}" target="_blank">{UPDATE_INFO.get('update_url', '#')}</a></p>
        </div>
    </div>
</body>
</html>
"""
        
        self.wfile.write(html.encode())
    
    def _generate_file_list_html(self):
        """生成文件列表HTML"""
        file_updates = UPDATE_INFO.get('file_updates', [])
        if not file_updates:
            return "<p>无更新文件</p>"
        
        html = ""
        for file in file_updates:
            action_text = "更新" if file['action'] == 'update' else "添加" if file['action'] == 'add' else "删除"
            html += f"""
            <div class="file">
                <div>{file['path']}</div>
                <div>{action_text}</div>
                <div>{file['size'] / 1024:.1f} KB</div>
            </div>
            """
        
        return html
    
    def _serve_update_info(self):
        """提供更新信息"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(UPDATE_INFO).encode())
    
    def _serve_check_api(self, query_params):
        """提供版本检查API"""
        # 获取客户端版本
        client_version = None
        if 'version' in query_params and query_params['version']:
            client_version = query_params['version'][0]
        
        if not client_version:
            # 未提供版本号
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "缺少version参数",
                "has_update": False
            }).encode())
            return
        
        # 检查是否有更新
        server_version = UPDATE_INFO.get('new_version', '0.0.0')
        has_update = self._is_higher_version(server_version, client_version)
        
        # 返回结果
        response = {
            "has_update": has_update,
            "client_version": client_version,
            "server_version": server_version
        }
        
        if has_update:
            response.update({
                "update_url": UPDATE_INFO.get('update_url', ''),
                "release_notes": UPDATE_INFO.get('release_notes', ''),
                "required_update": UPDATE_INFO.get('required_update', False)
            })
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def _serve_file(self, file_path):
        """提供文件下载"""
        # 安全检查，防止目录遍历攻击
        if ".." in file_path or file_path.startswith("/"):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"403 Forbidden")
            return
        
        # 拼接完整文件路径
        full_path = os.path.join(SERVER_DIR, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return
        
        # 获取文件大小
        file_size = os.path.getsize(full_path)
        
        # 获取文件类型
        content_type, _ = mimetypes.guess_type(full_path)
        if not content_type:
            content_type = "application/octet-stream"
        
        # 发送响应头
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        
        # 发送文件内容
        with open(full_path, "rb") as f:
            self.wfile.write(f.read())
    
    def _handle_publish(self):
        """处理发布更新请求"""
        global UPDATE_INFO
        
        # 获取Content-Length
        content_length = int(self.headers.get('Content-Length', 0))
        
        # 如果没有内容，返回错误
        if content_length == 0:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "请求体为空"
            }).encode())
            return
        
        # 读取请求体
        post_data = self.rfile.read(content_length)
        
        # 解析multipart/form-data
        import cgi
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': self.headers.get('Content-Type', ''),
            'CONTENT_LENGTH': str(content_length)
        }
        
        form = cgi.FieldStorage(
            fp=BytesIO(post_data),
            headers=self.headers,
            environ=environ
        )
        
        # 检查必要字段
        required_fields = ['app_name', 'version', 'release_notes']
        for field in required_fields:
            if field not in form:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"缺少必要字段: {field}"
                }).encode())
                return
        
        # 获取更新包文件
        if 'package' not in form:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "缺少更新包文件"
            }).encode())
            return
        
        # 保存更新包
        file_item = form['package']
        file_name = f"{form['app_name'].value}_update_to_{form['version'].value}.zip"
        file_path = os.path.join(SERVER_DIR, file_name)
        
        with open(file_path, 'wb') as f:
            f.write(file_item.file.read())
        
        # 更新版本信息
        UPDATE_INFO = {
            "app_name": form['app_name'].value,
            "old_version": UPDATE_INFO.get('new_version', '0.0.0'),
            "new_version": form['version'].value,
            "update_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_timestamp": int(time.time()),
            "update_url": f"/download/{file_name}",
            "check_url": "/updates.json",
            "release_notes": form['release_notes'].value,
            "required_update": form.getvalue('required_update', '').lower() == 'true',
            "update_size": os.path.getsize(file_path),
            "file_updates": []  # 暂不解析更新文件列表
        }
        
        # 保存更新信息
        with open(os.path.join(SERVER_DIR, "updates.json"), 'w', encoding='utf-8') as f:
            json.dump(UPDATE_INFO, f, ensure_ascii=False, indent=2)
        
        # 返回成功
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": True,
            "message": "更新已发布",
            "update_url": UPDATE_INFO['update_url'],
            "check_url": UPDATE_INFO['check_url']
        }).encode())
    
    def _is_higher_version(self, version1, version2):
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


def load_update_info():
    """加载更新信息"""
    global UPDATE_INFO
    
    update_info_path = os.path.join(SERVER_DIR, "updates.json")
    
    # 如果更新信息文件不存在，创建默认的
    if not os.path.exists(update_info_path):
        UPDATE_INFO = {
            "app_name": "松瓷机电AI助手",
            "old_version": "1.0.0",
            "new_version": "1.0.1",
            "update_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_timestamp": int(time.time()),
            "update_url": "/download/松瓷机电AI助手_update_to_1.0.1.zip",
            "check_url": "/updates.json",
            "release_notes": "初始版本",
            "required_update": False,
            "update_size": 0,
            "file_updates": []
        }
        
        # 保存默认更新信息
        with open(update_info_path, 'w', encoding='utf-8') as f:
            json.dump(UPDATE_INFO, f, ensure_ascii=False, indent=2)
    else:
        # 加载更新信息
        with open(update_info_path, 'r', encoding='utf-8') as f:
            UPDATE_INFO = json.load(f)


def start_server():
    """启动服务器"""
    global SERVER_PORT, SERVER_DIR
    
    # 确保更新包目录存在
    os.makedirs(SERVER_DIR, exist_ok=True)
    
    # 加载更新信息
    load_update_info()
    
    # 创建服务器
    server = HTTPServer(("0.0.0.0", SERVER_PORT), UpdateServerHandler)
    
    print(f"更新服务器已启动: http://localhost:{SERVER_PORT}")
    print(f"更新检查URL: http://localhost:{SERVER_PORT}/updates.json")
    print(f"更新包目录: {os.path.abspath(SERVER_DIR)}")
    print("按Ctrl+C停止服务器")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("服务器已停止")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="简单的更新服务器示例")
    parser.add_argument("-p", "--port", type=int, default=DEFAULT_PORT, help=f"服务器端口 (默认: {DEFAULT_PORT})")
    parser.add_argument("-d", "--dir", type=str, default=DEFAULT_DIR, help=f"更新包目录 (默认: {DEFAULT_DIR})")
    args = parser.parse_args()
    
    global SERVER_PORT, SERVER_DIR
    SERVER_PORT = args.port
    SERVER_DIR = args.dir


def main():
    """主函数"""
    # 解析命令行参数
    parse_arguments()
    
    # 启动服务器
    start_server()


# BytesIO用于模拟文件对象
from io import BytesIO

if __name__ == "__main__":
    main() 