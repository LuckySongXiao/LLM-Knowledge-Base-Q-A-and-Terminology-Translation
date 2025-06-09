import time
import threading
import pyperclip
from PySide6.QtWidgets import QApplication, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QObject, QEvent
from PySide6.QtGui import QCursor, QKeyEvent

class TextSelectionSignals(QObject):
    """文本选择信号"""
    text_selected = Signal(str)

class FloatingTranslationWindow(QLabel):
    """悬浮翻译窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        """初始化UI"""
        # 设置窗口样式
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setWordWrap(True)
        self.setStyleSheet("""
            background-color: #f5f5f5;
            color: #333333;
            border: 1px solid #cccccc;
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        """)
        self.setMinimumWidth(250)
        self.setMaximumWidth(400)
        
        # 隐藏窗口
        self.hide()
    
    def showTranslation(self, original, translation, pos):
        """显示翻译结果"""
        # 设置内容
        self.setText(f"<b>原文:</b> {original}<br><br><b>翻译:</b> {translation}")
        
        # 计算窗口大小
        self.adjustSize()
        
        # 设置窗口位置
        screen_geometry = QApplication.primaryScreen().geometry()
        pos = QPoint(pos)
        
        # 确保窗口不会超出屏幕
        if pos.x() + self.width() > screen_geometry.width():
            pos.setX(screen_geometry.width() - self.width())
        if pos.y() + self.height() > screen_geometry.height():
            pos.setY(pos.y() - self.height())
        
        self.move(pos)
        self.show()
        
        # 设置定时器，5秒后自动关闭
        QTimer.singleShot(5000, self.hide)
    
    def mousePressEvent(self, event):
        """鼠标点击事件处理"""
        self.hide()

class TextMonitor:
    """文本监控类，监控用户选中的文本"""
    
    def __init__(self, translator):
        self.translator = translator
        self.is_monitoring = False
        self.monitor_thread = None
        self.signals = TextSelectionSignals()
        
        # 延迟创建悬浮窗口
        self.floating_window = None
    
    def _ensure_window_exists(self):
        """确保悬浮窗口已创建"""
        if self.floating_window is None:
            self.floating_window = FloatingTranslationWindow()
    
    def start_monitoring(self):
        """开始监控选中的文本"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_clipboard)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(1.0)
            self.monitor_thread = None
    
    def _monitor_clipboard(self):
        """监控剪贴板变化"""
        last_content = pyperclip.paste()
        
        while self.is_monitoring:
            try:
                # 检查当前选中的文本
                current_selection = self._get_selected_text()
                
                # 如果有选中的文本，且与上次不同
                if current_selection and current_selection != last_content:
                    last_content = current_selection
                    
                    # 发送信号
                    self.signals.text_selected.emit(current_selection)
                    
                    # 如果配置允许，显示悬浮翻译
                    if self.translator.settings.get('monitor_text', True):
                        # 确保已创建窗口
                        app = QApplication.instance()
                        if app:  # 只有在QApplication存在时才创建窗口
                            self._ensure_window_exists()
                            
                            translation = self.translator.translate_selected_text(current_selection)
                            
                            # 在主线程中更新UI
                            cursor_pos = QCursor.pos()
                            app.postEvent(
                                self.floating_window,
                                ShowTranslationEvent(current_selection, translation, cursor_pos)
                            )
            except Exception as e:
                print(f"文本监控错误: {e}")
                
            # 暂停一段时间
            time.sleep(0.5)
    
    def _get_selected_text(self):
        """获取当前选中的文本"""
        try:
            # 尝试使用剪贴板获取选中的文本
            app = QApplication.instance()
            if not app:
                return None
                
            clipboard = app.clipboard()
            mime_data = clipboard.mimeData()
            
            if mime_data.hasText():
                return mime_data.text()
            
            return None
        except Exception:
            # 如果出错，尝试使用pyperclip
            try:
                prev_clipboard = pyperclip.paste()
                
                # 模拟Ctrl+C
                app = QApplication.instance()
                if not app:
                    return None
                    
                focused_widget = app.focusWidget()
                if focused_widget:
                    app.postEvent(
                        focused_widget,
                        KeyEvent(QEvent.KeyPress, Qt.Key_C, Qt.ControlModifier)
                    )
                
                # 等待剪贴板更新
                time.sleep(0.1)
                
                # 获取选中的文本
                selected_text = pyperclip.paste()
                
                # 恢复之前的剪贴板内容
                pyperclip.copy(prev_clipboard)
                
                return selected_text if selected_text != prev_clipboard else None
            except Exception:
                return None

# 自定义事件，用于在主线程中更新UI
class ShowTranslationEvent(QEvent):
    """显示翻译事件"""
    
    EVENT_TYPE = QEvent.Type(QEvent.User + 1)
    
    def __init__(self, original, translation, pos):
        super().__init__(self.EVENT_TYPE)
        self.original = original
        self.translation = translation
        self.pos = pos
        
    def type(self):
        """获取事件类型"""
        return self.EVENT_TYPE
        
    def process(self, receiver):
        """处理事件"""
        cursor_pos = QCursor.pos()
        receiver.showTranslation(self.original, self.translation, cursor_pos)
        return True 