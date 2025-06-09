#!/usr/bin/env python3
"""
松瓷机电AI助手WEB UI测试脚本
用于测试WEB UI的基本功能是否正常
"""

import os
import sys
import time
import requests
import threading
from web_ui.app import create_app

def test_web_ui():
    """测试WEB UI功能"""
    print("=" * 60)
    print("松瓷机电AI助手WEB UI测试")
    print("=" * 60)
    
    # 创建测试应用
    print("[1/5] 创建Flask应用...")
    try:
        app, socketio = create_app('testing')
        print("✓ Flask应用创建成功")
    except Exception as e:
        print(f"✗ Flask应用创建失败: {e}")
        return False
    
    # 启动测试服务器
    print("[2/5] 启动测试服务器...")
    server_thread = None
    try:
        def run_server():
            socketio.run(app, host='127.0.0.1', port=5001, debug=False, use_reloader=False)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(3)
        print("✓ 测试服务器启动成功")
    except Exception as e:
        print(f"✗ 测试服务器启动失败: {e}")
        return False
    
    # 测试基本路由
    print("[3/5] 测试基本路由...")
    base_url = "http://127.0.0.1:5001"
    
    routes_to_test = [
        ('/', '主页'),
        ('/chat', '聊天页面'),
        ('/translation', '翻译页面'),
        ('/knowledge', '知识库页面'),
        ('/settings', '设置页面'),
        ('/voice', '语音页面'),
        ('/health', '健康检查')
    ]
    
    for route, name in routes_to_test:
        try:
            response = requests.get(base_url + route, timeout=5)
            if response.status_code == 200:
                print(f"  ✓ {name} ({route})")
            else:
                print(f"  ✗ {name} ({route}) - 状态码: {response.status_code}")
        except Exception as e:
            print(f"  ✗ {name} ({route}) - 错误: {e}")
    
    # 测试API接口
    print("[4/5] 测试API接口...")
    api_endpoints = [
        ('/api/chat/status', 'GET', '聊天状态'),
        ('/api/translation/languages', 'GET', '支持语言'),
        ('/api/knowledge/status', 'GET', '知识库状态'),
        ('/api/settings/system_info', 'GET', '系统信息'),
        ('/api/voice/status', 'GET', '语音状态')
    ]
    
    for endpoint, method, name in api_endpoints:
        try:
            if method == 'GET':
                response = requests.get(base_url + endpoint, timeout=5)
            else:
                response = requests.post(base_url + endpoint, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'success' in data or 'status' in data:
                    print(f"  ✓ {name} ({endpoint})")
                else:
                    print(f"  ⚠ {name} ({endpoint}) - 响应格式异常")
            else:
                print(f"  ✗ {name} ({endpoint}) - 状态码: {response.status_code}")
        except Exception as e:
            print(f"  ✗ {name} ({endpoint}) - 错误: {e}")
    
    # 测试静态文件
    print("[5/5] 测试静态文件...")
    static_files = [
        ('/static/css/style.css', 'CSS样式文件'),
        ('/static/js/app.js', 'JavaScript文件')
    ]
    
    for file_path, name in static_files:
        try:
            response = requests.get(base_url + file_path, timeout=5)
            if response.status_code == 200:
                print(f"  ✓ {name}")
            else:
                print(f"  ✗ {name} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"  ✗ {name} - 错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("如果所有测试都通过，您可以运行以下命令启动WEB UI:")
    print("  python web_ui/app.py")
    print("或者使用启动脚本:")
    print("  start_web_ui.bat (Windows)")
    print("  bash start_web_ui.sh (Linux/macOS)")
    print("=" * 60)
    
    return True

def check_dependencies():
    """检查依赖包"""
    print("检查WEB UI依赖包...")
    
    required_packages = [
        'flask',
        'flask_socketio',
        'flask_cors'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n缺少依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        print("  pip install -r web_ui/requirements.txt")
        return False
    
    print("✓ 所有依赖包已安装")
    return True

def main():
    """主函数"""
    print("松瓷机电AI助手WEB UI测试工具")
    print("此工具将测试WEB UI的基本功能")
    print()
    
    # 检查依赖
    if not check_dependencies():
        return
    
    print()
    
    # 运行测试
    try:
        test_web_ui()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
