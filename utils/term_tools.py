"""术语库工具模块，提供启动术语工具的功能"""

import os
import sys
import traceback

# 全局变量，保持对术语工具窗口的引用
term_tool_window = None

def launch_emergency_term_tool():
    """启动术语库应急工具"""
    try:
        print("[INFO] 正在启动术语库应急工具...")
        
        # 确保应急工具文件存在
        tool_path = os.path.join('utils', 'emergency_term_tool.py')
        if not os.path.exists(tool_path):
            print(f"[ERROR] 术语库应急工具文件不存在: {tool_path}")
            return False
        
        # 导入应急工具模块并创建窗口
        from utils.emergency_term_tool import EmergencyTermTool
        
        # 检查是否已存在应用程序实例
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        
        # 创建窗口并保持引用，防止被垃圾回收
        # 注意：我们需要将窗口存储为全局变量或类属性，以防止它被垃圾回收
        global term_tool_window
        term_tool_window = EmergencyTermTool()
        term_tool_window.show()
        
        print("[INFO] 术语库应急工具已启动")
        return True
    
    except Exception as e:
        print(f"[ERROR] 启动术语库应急工具失败: {e}")
        traceback.print_exc()
        return False

def import_terminology_file(file_path=None):
    """导入术语库文件"""
    try:
        # 启动术语工具
        from utils.emergency_term_tool import EmergencyTermTool
        
        # 创建工具实例
        app = None
        if not sys.modules.get('PySide6.QtWidgets').QApplication.instance():
            from PySide6.QtWidgets import QApplication
            app = QApplication(sys.argv)
        
        tool = EmergencyTermTool()
        
        # 如果指定了文件路径，直接导入
        if file_path and os.path.exists(file_path):
            tool.import_terms_from_file(file_path)
            # 自动生成向量
            tool.generate_vectors()
        
        # 显示工具界面
        tool.show()
        
        # 如果创建了应用程序实例，则运行主循环
        if app:
            return app.exec()
        
        return True
    
    except Exception as e:
        print(f"[ERROR] 导入术语文件失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 直接测试
    launch_emergency_term_tool() 