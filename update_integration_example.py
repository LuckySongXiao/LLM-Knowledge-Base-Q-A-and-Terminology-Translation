#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
update_integration_example.py - 自动更新集成示例

此脚本展示如何在松瓷机电AI助手程序中集成自动更新功能。
"""

import sys
import os
import threading
import time
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QProgressBar, QLabel, QPushButton, QVBoxLayout, QWidget

# 导入自动更新器
from auto_updater import AutoUpdater

class UpdateDialog(QWidget):
    """更新提示对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("软件更新")
        self.resize(400, 150)
        
        # 设置布局
        layout = QVBoxLayout()
        
        # 创建更新状态标签
        self.status_label = QLabel("正在检查更新...")
        layout.addWidget(self.status_label)
        
        # 创建版本信息标签
        self.version_label = QLabel("")
        layout.addWidget(self.version_label)
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 创建按钮布局
        self.update_button = QPushButton("更新")
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(self.start_update)
        
        self.later_button = QPushButton("稍后提醒")
        self.later_button.clicked.connect(self.close)
        
        self.restart_button = QPushButton("立即重启")
        self.restart_button.setEnabled(False)
        self.restart_button.clicked.connect(self.restart_app)
        
        # 添加按钮到布局
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.later_button)
        button_layout.addWidget(self.restart_button)
        layout.addLayout(button_layout)
        
        # 设置主布局
        self.setLayout(layout)
        
        # 创建更新器
        self.updater = AutoUpdater(
            check_url="https://example.com/updates.json",
            on_progress=self.update_progress
        )
        
        # 检查更新的线程
        self.check_thread = None
        self.has_update = False
        self.current_version = ""
        self.latest_version = ""
        
        # 自动开始检查更新
        self.check_for_updates()
    
    def check_for_updates(self):
        """检查更新"""
        # 禁用按钮
        self.update_button.setEnabled(False)
        self.later_button.setEnabled(False)
        
        # 创建并启动线程
        self.check_thread = threading.Thread(target=self._check_thread_func)
        self.check_thread.daemon = True
        self.check_thread.start()
    
    def _check_thread_func(self):
        """检查更新的线程函数"""
        try:
            # 检查更新
            has_update, current_version, latest_version = self.updater.check_for_updates()
            
            # 更新UI（在主线程中）
            QApplication.instance().postEvent(
                self,
                UpdateResultEvent(has_update, current_version, latest_version)
            )
        except Exception as e:
            # 更新检查失败
            QApplication.instance().postEvent(
                self,
                UpdateErrorEvent(str(e))
            )
    
    def update_result(self, has_update, current_version, latest_version):
        """处理更新检查结果"""
        self.has_update = has_update
        self.current_version = current_version
        self.latest_version = latest_version
        
        if has_update:
            self.status_label.setText(f"发现新版本: {latest_version}")
            self.version_label.setText(f"当前版本: {current_version}")
            self.update_button.setEnabled(True)
            self.later_button.setEnabled(True)
        else:
            self.status_label.setText("当前已是最新版本")
            self.version_label.setText(f"版本: {current_version}")
            self.progress_bar.setValue(100)
            
            # 3秒后自动关闭
            QApplication.instance().postEvent(
                self,
                AutoCloseEvent(3000)
            )
    
    def update_error(self, error_message):
        """处理更新检查错误"""
        self.status_label.setText(f"检查更新失败: {error_message}")
        self.later_button.setEnabled(True)
    
    def start_update(self):
        """开始更新"""
        # 禁用按钮
        self.update_button.setEnabled(False)
        self.later_button.setEnabled(False)
        
        # 更新状态
        self.status_label.setText("准备更新...")
        
        # 开始下载更新
        self.updater.download_updates()
    
    def update_progress(self, progress, message):
        """更新进度回调函数"""
        # 在主线程中更新UI
        QApplication.instance().postEvent(
            self,
            UpdateProgressEvent(progress, message)
        )
    
    def handle_progress_update(self, progress, message):
        """处理进度更新事件"""
        self.progress_bar.setValue(int(progress * 100))
        self.status_label.setText(message)
        
        # 如果更新完成，启用重启按钮
        if progress >= 1.0:
            self.restart_button.setEnabled(True)
            self.later_button.setText("关闭")
            self.later_button.setEnabled(True)
    
    def restart_app(self):
        """重启应用"""
        self.updater.restart_application()
    
    def auto_close(self, delay):
        """自动关闭对话框"""
        self.delay_close_timer = self.startTimer(delay)
    
    def timerEvent(self, event):
        """定时器事件"""
        if hasattr(self, 'delay_close_timer') and event.timerId() == self.delay_close_timer:
            self.killTimer(self.delay_close_timer)
            self.close()
    
    def event(self, event):
        """自定义事件处理"""
        if isinstance(event, UpdateResultEvent):
            self.update_result(event.has_update, event.current_version, event.latest_version)
            return True
        elif isinstance(event, UpdateErrorEvent):
            self.update_error(event.error_message)
            return True
        elif isinstance(event, UpdateProgressEvent):
            self.handle_progress_update(event.progress, event.message)
            return True
        elif isinstance(event, AutoCloseEvent):
            self.auto_close(event.delay)
            return True
        return super().event(event)


# 自定义事件类型
from PySide6.QtCore import QEvent

class UpdateResultEvent(QEvent):
    """更新检查结果事件"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, has_update, current_version, latest_version):
        super().__init__(self.EVENT_TYPE)
        self.has_update = has_update
        self.current_version = current_version
        self.latest_version = latest_version

class UpdateErrorEvent(QEvent):
    """更新错误事件"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, error_message):
        super().__init__(self.EVENT_TYPE)
        self.error_message = error_message

class UpdateProgressEvent(QEvent):
    """更新进度事件"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, progress, message):
        super().__init__(self.EVENT_TYPE)
        self.progress = progress
        self.message = message

class AutoCloseEvent(QEvent):
    """自动关闭事件"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, delay):
        super().__init__(self.EVENT_TYPE)
        self.delay = delay


class MainWindow(QMainWindow):
    """示例主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("松瓷机电AI助手")
        self.resize(800, 600)
        
        # 创建中心部件和布局
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # 添加检查更新按钮
        update_button = QPushButton("检查更新")
        update_button.clicked.connect(self.check_for_updates)
        layout.addWidget(update_button)
        
        # 设置中心部件
        self.setCentralWidget(central_widget)
        
        # 自动更新相关属性
        self.last_check_time = 0
        self.check_interval = 24 * 60 * 60  # 24小时检查一次
        
        # 程序启动时检查更新
        self.check_for_updates_if_needed()
    
    def check_for_updates_if_needed(self):
        """如果需要，检查更新"""
        current_time = time.time()
        
        # 如果距离上次检查时间超过了检查间隔，则检查更新
        if current_time - self.last_check_time > self.check_interval:
            # 延迟3秒后检查，让应用先完成启动
            QApplication.instance().processEvents()
            self.startTimer(3000)
    
    def timerEvent(self, event):
        """定时器事件，用于延迟检查更新"""
        self.killTimer(event.timerId())
        self.check_for_updates()
    
    def check_for_updates(self):
        """检查更新"""
        # 更新上次检查时间
        self.last_check_time = time.time()
        
        # 创建并显示更新对话框
        update_dialog = UpdateDialog(self)
        update_dialog.show()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 