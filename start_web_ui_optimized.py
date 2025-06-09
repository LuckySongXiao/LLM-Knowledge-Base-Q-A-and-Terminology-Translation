#!/usr/bin/env python3
"""
优化的 WEB UI 启动脚本
避免模型重复加载，提高资源利用效率
"""

import os
import sys
import time

def main():
    """主函数"""
    print("🚀 启动优化的 松瓷机电AI助手 WEB UI 服务...")
    
    # 设置环境变量，禁用 Flask 自动重启
    os.environ['FLASK_ENV'] = 'production'  # 使用生产模式避免自动重启
    os.environ['FLASK_DEBUG'] = '0'         # 禁用调试模式
    
    # 添加项目根目录到Python路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        # 导入并启动应用
        from web_ui.app import main as web_main
        
        print("📋 优化配置:")
        print("  - 禁用 Flask 自动重启")
        print("  - 启用模型缓存机制")
        print("  - 生产模式运行")
        print()
        
        # 启动WEB应用
        web_main()
        
    except KeyboardInterrupt:
        print("\n⏹️  服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
