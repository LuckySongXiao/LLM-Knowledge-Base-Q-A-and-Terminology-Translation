from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer

class LoadingScreen(QDialog):
    """模型加载界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("加载中...")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 标题
        self.title_label = QLabel("正在加载AI模型...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.title_label)
        
        # 当前加载模型
        self.model_label = QLabel("准备中...")
        self.model_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.model_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 状态信息
        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def update_progress(self, model_name, progress):
        """更新加载进度"""
        self.model_label.setText(f"正在加载: {model_name}")
        self.progress_bar.setValue(int(progress * 100))
        
        if progress < 0.5:
            self.status_label.setText("加载模型文件...")
        elif progress < 0.8:
            self.status_label.setText("初始化模型...")
        else:
            self.status_label.setText("即将完成...")
    
    def set_complete(self, model_name):
        """设置加载完成状态"""
        self.model_label.setText(f"已加载: {model_name}")
        self.progress_bar.setValue(100)
        self.status_label.setText("加载完成!")
    
    def set_error(self, model_name, error):
        """设置加载错误状态"""
        self.model_label.setText(f"加载失败: {model_name}")
        self.status_label.setText(f"错误: {error}")
        self.status_label.setStyleSheet("color: red;")
    
    def close_after_delay(self, delay_ms=500):
        """延迟关闭"""
        QTimer.singleShot(delay_ms, self.accept) 