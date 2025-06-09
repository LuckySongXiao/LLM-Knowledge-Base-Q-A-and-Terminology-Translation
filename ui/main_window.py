from PySide6.QtWidgets import QMainWindow, QTabWidget, QMenu, QMessageBox, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtGui import QAction, QShortcut, QKeySequence
from PySide6.QtCore import Qt, QTimer
from ui.settings_panel import SettingsPanel
from ui.chat_panel import ChatPanel
from ui.translation_panel import TranslationPanel
from ui.knowledge_panel import KnowledgePanel
from ui.voice_panel import VoicePanel

class MainWindow(QMainWindow):
    """松瓷机电AI助手主窗口"""
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.i18n = assistant.i18n
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI界面"""
        # 设置窗口标题和大小
        self.setWindowTitle(self.i18n.translate("app_title"))
        self.resize(1000, 700)
        
        # 创建主标签页
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 添加各功能面板
        self.chat_panel = ChatPanel(self.assistant)
        self.tabs.addTab(self.chat_panel, self.i18n.translate("chat"))
        
        self.translation_panel = TranslationPanel(self.assistant)
        self.tabs.addTab(self.translation_panel, self.i18n.translate("translation"))
        
        self.knowledge_panel = KnowledgePanel(self.assistant)
        self.tabs.addTab(self.knowledge_panel, self.i18n.translate("knowledge_base"))
        
        self.settings_panel = SettingsPanel(self.assistant)
        self.tabs.addTab(self.settings_panel, self.i18n.translate("settings"))
        
        # 恢复术语库按钮 - 在顶部工具栏上添加
        #tool_bar = self.addToolBar("工具栏")
        #tool_bar.setMovable(False)
        #tool_bar.setFloatable(False)
        #tool_bar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)
        
        #self.term_tool_btn = QPushButton("术语库")  # 固定使用中文
        #self.term_tool_btn.setStyleSheet("font-weight: bold; padding: 5px 10px;")
        #self.term_tool_btn.clicked.connect(self.launch_term_tool)
        
        # 将按钮包装到QWidget中以添加到工具栏
        #tool_widget = QWidget()
        #tool_layout = QHBoxLayout(tool_widget)
        #tool_layout.setContentsMargins(0, 0, 0, 0)
        #tool_layout.addWidget(self.term_tool_btn)
        #tool_bar.addWidget(tool_widget)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建状态栏
        self.statusBar().showMessage(self.i18n.translate("ready"))
    
    def create_menu(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = self.menuBar().addMenu(self.i18n.translate("file"))
        
        import_action = QAction(self.i18n.translate("import_doc"), self)
        import_action.triggered.connect(self.import_document)
        file_menu.addAction(import_action)
        
        export_action = QAction(self.i18n.translate("export_chat"), self)
        export_action.triggered.connect(self.export_chat)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(self.i18n.translate("exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 知识库菜单
        knowledge_menu = self.menuBar().addMenu(self.i18n.translate("knowledge_base"))
        
        manage_knowledge_action = QAction(self.i18n.translate("manage_knowledge"), self)
        manage_knowledge_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.knowledge_panel))
        knowledge_menu.addAction(manage_knowledge_action)
        
        # 语言菜单
        language_menu = self.menuBar().addMenu(self.i18n.translate("language"))
        
        chinese_action = QAction("中文", self)
        chinese_action.triggered.connect(lambda: self.change_language("zh"))
        language_menu.addAction(chinese_action)
        
        english_action = QAction("English", self)
        english_action.triggered.connect(lambda: self.change_language("en"))
        language_menu.addAction(english_action)
        
        # 添加术语库菜单项 - 使用固定中文
        term_action = self.menuBar().addAction("术语库")
        term_action.triggered.connect(self.launch_term_tool)
    
    def import_document(self):
        """导入文档到知识库"""
        self.tabs.setCurrentWidget(self.knowledge_panel)
        self.knowledge_panel.import_document()
    
    def export_chat(self):
        """导出对话"""
        # 实现导出对话的功能
        pass
    
    def change_language(self, lang_code):
        """切换语言"""
        self.assistant.i18n.set_language(lang_code)
        self.assistant.settings.set('language', lang_code)
        
        # 刷新UI文本
        QMessageBox.information(
            self, 
            self.i18n.translate("language_changed"),
            self.i18n.translate("restart_to_apply")
        )
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            self.i18n.translate("about"),
            self.i18n.translate("about_content")
        )
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        self.assistant.shutdown()
        event.accept()

    def setup_actions(self):
        """设置菜单动作"""
        # 添加知识库菜单项
        knowledge_action = self.menu_bar.addAction(self.i18n.translate("knowledge_base"))
        knowledge_action.triggered.connect(self.show_knowledge_panel)
        
        # 添加设置菜单项
        settings_action = self.menu_bar.addAction(self.i18n.translate("settings"))
        settings_action.triggered.connect(self.show_settings_panel)

    def show_knowledge_panel(self):
        """显示知识库面板"""
        # 检查向量模型是否已加载
        if not hasattr(self.assistant.vector_db, 'model') or self.assistant.vector_db.model is None:
            QMessageBox.warning(
                self,
                self.assistant.i18n.translate("warning"),
                "向量模型正在加载中，请稍后再试。\n知识库功能需要向量模型支持。"
            )
            return
        
        if not hasattr(self, 'knowledge_panel'):
            self.knowledge_panel = KnowledgePanel(self.assistant)
        self.knowledge_panel.show()

    def show_settings_panel(self):
        """显示设置面板"""
        self.tabs.setCurrentWidget(self.settings_panel)
        self.settings_panel.show()

    def launch_term_tool(self):
        """启动术语库应急工具"""
        try:
            print("\n===== 启动术语库应急工具 =====")
            
            # 显示加载中状态
            self.statusBar().showMessage("正在启动术语库工具...", 2000)
            
            # 导入工具启动器
            from utils.term_tools import launch_emergency_term_tool
            
            # 启动应急工具
            success = launch_emergency_term_tool()
            
            if success:
                print("术语库应急工具启动成功")
                self.statusBar().showMessage("术语库工具已启动", 5000)
            else:
                print("术语库应急工具启动失败")
                QMessageBox.critical(self, "错误", "术语库应急工具启动失败")
                self.statusBar().showMessage("术语库工具启动失败", 5000)
        
        except Exception as e:
            print(f"启动术语应急工具时出错: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"启动术语工具失败: {str(e)}")
        
        print("===== 术语工具处理完成 =====\n") 