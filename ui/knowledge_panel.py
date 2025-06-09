from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QTabWidget, QListWidget, QFileDialog,
                             QLabel, QLineEdit, QMessageBox, QSplitter)
from PySide6.QtCore import Qt

class KnowledgePanel(QWidget):
    """知识库和术语库管理面板"""
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.i18n = assistant.i18n
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建选项卡
        tabs = QTabWidget()
        
        # 知识库选项卡
        knowledge_tab = QWidget()
        self.setup_knowledge_tab(knowledge_tab)
        tabs.addTab(knowledge_tab, self.i18n.translate("knowledge_base"))
        
        # 术语库选项卡
        term_tab = QWidget()
        self.setup_term_tab(term_tab)
        tabs.addTab(term_tab, self.i18n.translate("term_base"))
        
        layout.addWidget(tabs)
        self.setLayout(layout)
    
    def setup_knowledge_tab(self, tab):
        """设置知识库选项卡"""
        layout = QVBoxLayout()
        
        # 知识条目搜索
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(self.i18n.translate("search")))
        
        self.knowledge_search = QLineEdit()
        self.knowledge_search.setPlaceholderText(self.i18n.translate("search_knowledge"))
        self.knowledge_search.returnPressed.connect(self.search_knowledge)
        search_layout.addWidget(self.knowledge_search)
        
        search_button = QPushButton(self.i18n.translate("search"))
        search_button.clicked.connect(self.search_knowledge)
        search_layout.addWidget(search_button)
        
        layout.addLayout(search_layout)
        
        # 知识条目列表和内容显示
        splitter = QSplitter(Qt.Horizontal)
        
        self.knowledge_list = QListWidget()
        self.knowledge_list.itemSelectionChanged.connect(self.show_knowledge_content)
        splitter.addWidget(self.knowledge_list)
        
        # 右侧区域包含内容和元数据
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 内容编辑区
        content_label = QLabel(self.i18n.translate("content"))
        right_layout.addWidget(content_label)
        
        self.knowledge_content = QTextEdit()
        right_layout.addWidget(self.knowledge_content)
        
        # 元数据显示区域
        metadata_label = QLabel(self.i18n.translate("metadata"))
        right_layout.addWidget(metadata_label)
        
        self.metadata_text = QTextEdit()
        self.metadata_text.setMaximumHeight(100)  # 限制高度
        self.metadata_text.setReadOnly(True)      # 设为只读
        right_layout.addWidget(self.metadata_text)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)  # 添加widget，不是layout
        
        layout.addWidget(splitter)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        import_button = QPushButton(self.i18n.translate("import_document"))
        import_button.clicked.connect(self.import_document)
        button_layout.addWidget(import_button)
        
        add_button = QPushButton(self.i18n.translate("add_knowledge"))
        add_button.clicked.connect(self.add_knowledge)
        button_layout.addWidget(add_button)
        
        save_button = QPushButton(self.i18n.translate("save_knowledge"))
        save_button.clicked.connect(self.save_knowledge)
        button_layout.addWidget(save_button)
        
        delete_button = QPushButton(self.i18n.translate("delete_knowledge"))
        delete_button.clicked.connect(self.delete_knowledge)
        button_layout.addWidget(delete_button)
        
        layout.addLayout(button_layout)
        
        tab.setLayout(layout)
        
        # 加载知识条目
        self.load_knowledge_items()
    
    def setup_term_tab(self, tab):
        """设置术语库选项卡"""
        layout = QVBoxLayout()
        
        # 术语搜索
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(self.i18n.translate("search")))
        
        self.term_search = QLineEdit()
        self.term_search.setPlaceholderText(self.i18n.translate("search_term"))
        self.term_search.returnPressed.connect(self.search_term)
        search_layout.addWidget(self.term_search)
        
        search_button = QPushButton(self.i18n.translate("search"))
        search_button.clicked.connect(self.search_term)
        search_layout.addWidget(search_button)
        
        layout.addLayout(search_layout)
        
        # 术语列表和解释
        splitter = QSplitter(Qt.Horizontal)
        
        self.term_list = QListWidget()
        self.term_list.currentRowChanged.connect(self.show_term_item)
        splitter.addWidget(self.term_list)
        
        term_detail_widget = QWidget()
        term_detail_layout = QVBoxLayout()
        term_detail_widget.setLayout(term_detail_layout)
        
        term_detail_layout.addWidget(QLabel(self.i18n.translate("term")))
        self.term_name = QLineEdit()
        term_detail_layout.addWidget(self.term_name)
        
        term_detail_layout.addWidget(QLabel(self.i18n.translate("definition")))
        self.term_definition = QTextEdit()
        term_detail_layout.addWidget(self.term_definition)
        
        splitter.addWidget(term_detail_widget)
        
        layout.addWidget(splitter)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        import_button = QPushButton(self.i18n.translate("import_terms"))
        import_button.clicked.connect(self.import_terms)
        button_layout.addWidget(import_button)
        
        add_button = QPushButton(self.i18n.translate("add_term"))
        add_button.clicked.connect(self.add_term)
        button_layout.addWidget(add_button)
        
        save_button = QPushButton(self.i18n.translate("save_term"))
        save_button.clicked.connect(self.save_term)
        button_layout.addWidget(save_button)
        
        delete_button = QPushButton(self.i18n.translate("delete_term"))
        delete_button.clicked.connect(self.delete_term)
        button_layout.addWidget(delete_button)
        
        layout.addLayout(button_layout)
        
        tab.setLayout(layout)
        
        # 加载术语条目
        self.load_term_items()
    
    def load_knowledge_items(self):
        """加载知识条目"""
        self.knowledge_list.clear()
        items = self.assistant.knowledge_base.list_items()
        for item in items:
            self.knowledge_list.addItem(item)
    
    def load_term_items(self):
        """加载术语条目"""
        self.term_list.clear()
        terms = self.assistant.term_base.list_terms()
        for term in terms:
            self.term_list.addItem(term)
    
    def search_knowledge(self):
        """搜索知识条目"""
        query = self.knowledge_search.text().strip()
        if not query:
            self.load_knowledge_items()
            return
            
        self.knowledge_list.clear()
        results = self.assistant.knowledge_base.search(query)
        for item in results:
            self.knowledge_list.addItem(item)
    
    def search_term(self):
        """搜索术语条目"""
        query = self.term_search.text().strip()
        if not query:
            self.load_term_items()
            return
            
        self.term_list.clear()
        results = self.assistant.term_base.search(query)
        for term in results:
            self.term_list.addItem(term)
    
    def show_knowledge_content(self):
        """显示选中知识条目的内容"""
        # 获取当前选中的项
        selected_items = self.knowledge_list.selectedItems()
        if not selected_items:
            self.knowledge_content.clear()
            return
        
        # 获取条目名称
        item_name = selected_items[0].text()
        
        try:
            # 从知识库获取条目内容
            item = self.assistant.knowledge_base.get_item(item_name)
            
            if not item:
                self.knowledge_content.setText(f"错误：找不到知识条目 '{item_name}'")
                return
            
            # 检查是否为字典类型（正常知识条目）
            if isinstance(item, dict) and 'content' in item:
                self.knowledge_content.setText(item['content'])
            # 检查是否为问答组类型
            elif isinstance(item, dict) and 'metadata' in item and item['metadata'].get('type') == 'qa_group':
                content = f"问题：{item['metadata'].get('question', '未知问题')}\n\n"
                content += f"答案：{item['metadata'].get('answer', '未知答案')}"
                self.knowledge_content.setText(content)
            else:
                # 尝试将内容转换为字符串
                self.knowledge_content.setText(str(item))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.knowledge_content.setText(f"加载内容时出错：{str(e)}")
    
    def show_term_item(self, row):
        """显示术语条目内容"""
        if row < 0:
            return
            
        term_name = self.term_list.item(row).text()
        definition = self.assistant.term_base.get_term(term_name)
        
        self.term_name.setText(term_name)
        self.term_definition.setText(definition)
    
    def import_document(self):
        """导入文档到知识库"""
        # 首先检查向量模型是否已加载
        if not hasattr(self.assistant.vector_db, 'model') or self.assistant.vector_db.model is None:
            QMessageBox.warning(
                self,
                self.i18n.translate("import_error"),
                "向量模型尚未加载完成，请等待模型下载完成后再试"
            )
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            self.i18n.translate("select_document"), 
            "", 
            "Text Files (*.txt *.md);;All Files (*)"
        )
        
        if file_path:
            try:
                success, message = self.assistant.knowledge_base.import_file(file_path)
                
                if success:
                    QMessageBox.information(self, self.i18n.translate("import_success"), message)
                    self.refresh_knowledge_list()
                else:
                    QMessageBox.critical(self, self.i18n.translate("import_error"), message)
            except Exception as e:
                QMessageBox.critical(self, self.i18n.translate("import_error"), str(e))
    
    def add_knowledge(self):
        """添加知识条目"""
        # 首先检查向量模型是否已加载
        if not hasattr(self.assistant.vector_db, 'model') or self.assistant.vector_db.model is None:
            QMessageBox.warning(
                self,
                "添加失败",
                "向量模型尚未加载完成，请等待模型下载完成后再试"
            )
            return
            
        # 创建输入对话框
        title, ok = QInputDialog.getText(
            self, 
            "添加知识条目", 
            "请输入知识条目标题:"
        )
        
        if ok and title:
            # 清空并设置内容编辑区
            self.knowledge_content.clear()
            self.knowledge_content.setPlaceholderText("请在此输入知识内容...")
            
            # 设置当前标题
            self.current_knowledge_title = title
            
            # 提示用户
            QMessageBox.information(self, self.i18n.translate("success"), 
                                   f"已创建'{title}'条目，请在编辑区输入内容，然后点击'保存'按钮。")
    
    def save_knowledge(self):
        """保存知识条目"""
        # 检查是否有当前编辑的条目
        if not hasattr(self, 'current_knowledge_title') or not self.current_knowledge_title:
            QMessageBox.warning(
                self,
                "保存失败",
                "没有正在编辑的知识条目，请先添加或选择一个条目"
            )
            return
            
        # 获取内容
        content = self.knowledge_content.toPlainText().strip()
        if not content:
            QMessageBox.warning(
                self,
                "保存失败",
                "知识内容不能为空"
            )
            return
            
        try:
            # 保存到知识库
            success = self.assistant.knowledge_base.add_knowledge(
                self.current_knowledge_title, 
                content
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "保存成功",
                    f"知识条目'{self.current_knowledge_title}'已保存"
                )
                # 刷新列表
                self.refresh_knowledge_list()
            else:
                QMessageBox.critical(
                    self,
                    "保存失败",
                    "知识条目保存失败，请检查日志获取详细信息"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "保存失败",
                f"保存知识条目时出错：{str(e)}"
            )
    
    def delete_knowledge(self):
        """删除知识条目"""
        # 获取当前选中的条目
        selected_items = self.knowledge_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                "删除失败",
                "请先选择要删除的知识条目"
            )
            return
            
        # 获取选中的条目名称
        item_name = selected_items[0].text()
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除知识条目'{item_name}'吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 从知识库中删除
                success = self.assistant.knowledge_base.delete_knowledge(item_name)
                
                if success:
                    QMessageBox.information(
                        self,
                        "删除成功",
                        f"知识条目'{item_name}'已删除"
                    )
                    # 刷新列表
                    self.refresh_knowledge_list()
                    # 清空内容区
                    self.knowledge_content.clear()
                else:
                    QMessageBox.critical(
                        self,
                        "删除失败",
                        "知识条目删除失败，请检查日志获取详细信息"
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "删除失败",
                    f"删除知识条目时出错：{str(e)}"
                )
    
    def import_terms(self):
        """导入术语表"""
        try:
            print("启动术语导入功能")
            
            # 使用术语库应急工具
            from utils.term_tools import launch_emergency_term_tool
            
            # 显示加载中状态
            self.assistant.main_window.statusBar().showMessage("正在启动术语管理工具...", 2000)
            
            # 启动术语库应急工具
            launch_emergency_term_tool()
            
            print("术语库工具已启动")
            self.assistant.main_window.statusBar().showMessage("术语库工具已启动", 5000)
        
        except Exception as e:
            print(f"启动术语导入功能失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"术语导入功能启动失败: {str(e)}")
    
    def add_term(self):
        """添加术语条目"""
        try:
            print("启动术语添加功能")
            
            # 使用术语库应急工具
            from utils.term_tools import launch_emergency_term_tool
            
            # 显示加载中状态
            self.assistant.main_window.statusBar().showMessage("正在启动术语管理工具...", 2000)
            
            # 启动术语库应急工具
            launch_emergency_term_tool()
            
            print("术语库工具已启动")
            self.assistant.main_window.statusBar().showMessage("术语库工具已启动", 5000)
        
        except Exception as e:
            print(f"启动术语添加功能失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"术语添加功能启动失败: {str(e)}")
    
    def save_term(self):
        """保存术语条目 - 重定向到工具"""
        self.add_term()
    
    def delete_term(self):
        """删除术语条目 - 重定向到工具"""
        self.add_term()
    
    def refresh_knowledge_list(self):
        """刷新知识库列表"""
        self.knowledge_list.clear()
        items = self.assistant.knowledge_base.list_items()
        for item in items:
            self.knowledge_list.addItem(item)
    
    def update_knowledge_item(self):
        """更新知识条目"""
        # 获取当前选中的项
        selected_items = self.knowledge_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.i18n.translate("warning"), 
                               self.i18n.translate("select_item_first"))
            return
        
        # 获取条目名称和新内容
        item_name = selected_items[0].text()
        new_content = self.knowledge_content.toPlainText()
        
        # 获取当前条目以保留元数据
        current_item = self.assistant.knowledge_base.get_item(item_name)
        metadata = current_item.get('metadata', {}) if isinstance(current_item, dict) else {}
        
        # 更新条目
        if self.assistant.knowledge_base.update_item(item_name, new_content, metadata):
            QMessageBox.information(self, self.i18n.translate("success"), 
                                   self.i18n.translate("item_updated"))
        else:
            QMessageBox.warning(self, self.i18n.translate("error"),
                               self.i18n.translate("update_failed")) 