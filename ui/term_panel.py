from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, 
                              QLabel, QTextEdit, QLineEdit, QMessageBox, QFileDialog, QDialog,
                              QFormLayout, QProgressDialog)
from PySide6.QtCore import Qt, QMetaObject, Q_ARG, QTimer, QCoreApplication
from PySide6.QtCore import Slot
import threading
import os
import sys

class TermPanel(QWidget):
    """术语管理面板"""
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.i18n = assistant.i18n
        self.setWindowTitle(self.i18n.translate("term_management"))
        
        # 清除重复实例化带来的问题
        if hasattr(self, '_initialized'):
            print("警告：术语面板实例被重复初始化")
            return
        self._initialized = True
        
        # 确保术语库和向量库已正确初始化
        self.verify_components() 
        
        # 初始化UI
        self.init_ui()
        
        # 立即连接信号 - 确保在init_ui之后
        self.connect_signals()
        
        # 加载术语列表
        self.load_term_list()
        
        # 确保面板尺寸合理
        self.resize(800, 600)
        
        # 自动诊断按钮
        self.diagnose_btn = QPushButton("诊断术语系统")
        self.diagnose_btn.clicked.connect(self.diagnose_term_system)
        layout = self.layout()
        if layout:
            layout.addWidget(self.diagnose_btn)
        
        # 打印调试信息
        print(f"术语面板初始化完成，按钮状态: {self.import_btn.isEnabled()}")
        
        # 在构造函数末尾再次强制连接信号
        QTimer.singleShot(500, self.ensure_signals_connected)
    
    def verify_components(self):
        """验证术语库组件是否正确初始化"""
        print("\n===== 术语库组件验证 =====")
        
        # 检查并确保术语向量数据库
        if not hasattr(self.assistant, 'term_vector_db'):
            print("[错误] 术语向量数据库未初始化，尝试创建")
            try:
                from core.term_vector_db import TermVectorDB
                self.assistant.term_vector_db = TermVectorDB(self.assistant.settings)
                print("[修复] 已创建术语向量数据库")
            except Exception as e:
                print(f"[严重] 无法创建术语向量数据库: {e}")
        else:
            print("[正常] 术语向量数据库已初始化")
        
        # 检查并确保术语库
        if not hasattr(self.assistant, 'term_base'):
            print("[错误] 术语库未初始化，尝试创建")
            try:
                from core.term_base import TermBase
                if hasattr(self.assistant, 'term_vector_db'):
                    self.assistant.term_base = TermBase(self.assistant.term_vector_db, self.assistant.settings)
                    print("[修复] 已创建术语库")
            except Exception as e:
                print(f"[严重] 无法创建术语库: {e}")
        else:
            print("[正常] 术语库已初始化")
            
        print("===== 验证完成 =====\n")
    
    def init_ui(self):
        """初始化UI"""
        # 创建布局
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel(self.i18n.translate("term_management"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 术语管理区域
        term_layout = QHBoxLayout()
        
        # 术语列表
        list_layout = QVBoxLayout()
        self.term_list = QListWidget()
        list_layout.addWidget(self.term_list)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.i18n.translate("search_term"))
        self.search_btn = QPushButton(self.i18n.translate("search"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        list_layout.addLayout(search_layout)
        
        # 术语操作按钮
        button_layout = QHBoxLayout()
        self.import_btn = QPushButton(self.i18n.translate("import"))
        self.add_btn = QPushButton(self.i18n.translate("add"))
        self.edit_btn = QPushButton(self.i18n.translate("edit"))
        self.delete_btn = QPushButton(self.i18n.translate("delete"))
        
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        
        list_layout.addLayout(button_layout)
        term_layout.addLayout(list_layout, 1)
        
        # 术语详情区域
        detail_layout = QVBoxLayout()
        self.term_details = QTextEdit()
        self.term_details.setReadOnly(True)
        detail_layout.addWidget(QLabel(self.i18n.translate("term_details")))
        detail_layout.addWidget(self.term_details)
        term_layout.addLayout(detail_layout, 2)
        
        main_layout.addLayout(term_layout)
        
        # 调试信息标签
        self.debug_label = QLabel("状态: 准备导入")
        main_layout.addWidget(self.debug_label)
        
        # 在底部添加应急功能按钮
        emergency_layout = QHBoxLayout()
        self.emergency_add_btn = QPushButton("应急添加术语")
        self.emergency_add_btn.setStyleSheet("background-color: #ffaa00; font-weight: bold;")
        self.emergency_add_btn.clicked.connect(self.emergency_add_term)
        
        self.emergency_import_btn = QPushButton("应急导入术语")
        self.emergency_import_btn.setStyleSheet("background-color: #ffaa00; font-weight: bold;")
        self.emergency_import_btn.clicked.connect(self.emergency_import)
        
        emergency_layout.addWidget(self.emergency_add_btn)
        emergency_layout.addWidget(self.emergency_import_btn)
        main_layout.addLayout(emergency_layout)
    
    def connect_signals(self):
        """连接信号与槽"""
        if self.signals_connected:
            print("信号已连接，避免重复连接")
            return
            
        # 标记为已连接
        self.signals_connected = True
        
        print("正在连接术语面板按钮信号...")
        
        # 强制断开所有旧连接
        try:
            self.import_btn.clicked.disconnect()
        except:
            pass
            
        # 直接连接到直接导入方法，不再使用debug_import
        self.import_btn.clicked.connect(self.direct_import)
        
        # 连接其他按钮事件
        try:
            self.add_btn.clicked.disconnect()
            self.edit_btn.clicked.disconnect()
            self.delete_btn.clicked.disconnect()
        except:
            pass
            
        self.add_btn.clicked.connect(self.add_term)
        self.edit_btn.clicked.connect(self.edit_term)
        self.delete_btn.clicked.connect(self.delete_term)
        
        # 连接列表选择事件
        try:
            self.term_list.itemSelectionChanged.disconnect()
        except:
            pass
            
        self.term_list.itemSelectionChanged.connect(self.show_term_details)
        
        # 连接搜索事件
        try:
            self.search_btn.clicked.disconnect()
            self.search_input.returnPressed.disconnect()
        except:
            pass
            
        self.search_btn.clicked.connect(self.search_terms)
        self.search_input.returnPressed.connect(self.search_terms)
        
        print("术语面板按钮信号连接完成")
    
    def load_term_list(self):
        """加载术语列表"""
        self.term_list.clear()
        terms = self.assistant.term_base.list_terms()
        for term in terms:
            self.term_list.addItem(term)
    
    def show_term_details(self):
        """术语选中事件"""
        selected_items = self.term_list.selectedItems()
        if not selected_items:
            self.term_details.clear()
            return
            
        term = selected_items[0].text()
        term_info = self.assistant.term_base.get_term_info(term)
        
        if term_info:
            # 格式化术语信息
            details = f"<h3>{term}</h3>\n"
            details += f"<p><b>{self.i18n.translate('source_language')}:</b> {term_info.get('source_language', '')}</p>\n"
            
            details += f"<h4>{self.i18n.translate('translations')}:</h4>\n"
            for lang, translation in term_info.get('translations', {}).items():
                details += f"<p><b>{lang}:</b> {translation}</p>\n"
            
            # 显示元数据
            if 'metadata' in term_info:
                details += f"<h4>{self.i18n.translate('metadata')}:</h4>\n"
                for key, value in term_info.get('metadata', {}).items():
                    details += f"<p><b>{key}:</b> {value}</p>\n"
            
            self.term_details.setHtml(details)
        else:
            self.term_details.clear()
    
    def direct_import(self):
        """直接处理导入功能"""
        try:
            self.debug_label.setText("准备导入术语文件...")
            print("开始术语导入流程")
            
            # 1. 确保术语库已正确初始化
            if not hasattr(self.assistant, 'term_base') or self.assistant.term_base is None:
                error_msg = "术语库组件未初始化"
                print(f"错误: {error_msg}")
                self.debug_label.setText(f"错误: {error_msg}")
                QMessageBox.critical(self, "组件错误", error_msg)
                return
            
            # 2. 选择文件
            options = QFileDialog.Options()
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "选择术语文件",
                "",
                "术语文件 (*.json *.csv *.tsv *.txt)",
                options=options
            )
            
            print(f"用户选择的文件: {filename}")
            self.debug_label.setText(f"已选择: {os.path.basename(filename) if filename else '无'}")
            
            if not filename:
                print("用户取消了文件选择")
                return
            
            # 3. 显示进度对话框
            progress = QProgressDialog("正在导入术语...", "取消", 0, 100, self)
            progress.setWindowTitle("导入中")
            progress.setWindowModality(Qt.WindowModal)
            progress.setValue(10)
            progress.show()
            QCoreApplication.processEvents()  # 确保UI更新
            
            # 4. 启动导入线程
            def run_import():
                try:
                    print(f"开始导入文件: {filename}")
                    success, message = self.assistant.term_base.import_terminology_file(filename)
                    
                    # 通知主线程
                    QMetaObject.invokeMethod(
                        self, "finish_import",
                        Qt.QueuedConnection,
                        Q_ARG(bool, success),
                        Q_ARG(str, message)
                    )
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    
                    # 通知主线程
                    QMetaObject.invokeMethod(
                        self, "finish_import",
                        Qt.QueuedConnection,
                        Q_ARG(bool, False),
                        Q_ARG(str, f"导入出错: {str(e)}")
                    )
            
            thread = threading.Thread(target=run_import)
            thread.daemon = True
            thread.start()
            
            # 更新进度
            def update_progress():
                if progress.wasCanceled():
                    return
                
                current = progress.value()
                if current < 90 and thread.is_alive():
                    progress.setValue(current + 10)
                    QTimer.singleShot(300, update_progress)
                else:
                    progress.setValue(100)
            
            QTimer.singleShot(300, update_progress)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"导入功能发生错误: {str(e)}"
            print(error_msg)
            self.debug_label.setText(f"错误: {str(e)}")
            QMessageBox.critical(self, "导入错误", error_msg)
    
    @Slot(bool, str)
    def finish_import(self, success, message):
        """导入完成处理"""
        if success:
            self.debug_label.setText(f"导入成功: {message}")
            QMessageBox.information(self, "导入成功", message)
            # 刷新术语列表
            self.load_term_list()
        else:
            self.debug_label.setText(f"导入失败: {message}")
            QMessageBox.warning(self, "导入失败", message)
    
    def add_term(self):
        """添加术语条目"""
        # 创建编辑对话框
        dialog = TermEditDialog(self, self.i18n)
        if dialog.exec():
            # 获取输入的术语信息
            source_term = dialog.source_term_input.text().strip()  # 中文术语
            source_lang = dialog.source_lang_input.text().strip()  # 默认zh
            target_term = dialog.target_term_input.text().strip()  # 外语定义
            target_lang = dialog.target_lang_input.text().strip()  # 默认en
            
            if not source_term or not target_term:
                QMessageBox.warning(
                    self, 
                    "警告",
                    "术语和定义不能为空"
                )
                return
            
            # 显示处理进度对话框
            progress = QProgressDialog("正在添加术语并训练向量...", "取消", 0, 100, self)
            progress.setWindowTitle("处理中")
            progress.setWindowModality(Qt.WindowModal)
            progress.setValue(10)
            progress.show()
            
            # 后台处理线程
            def add_term_task():
                try:
                    # 调用术语库添加术语
                    success = self.assistant.term_base.add_term(
                        source_term, target_term, source_lang, target_lang
                    )
                    
                    # 更新进度
                    QMetaObject.invokeMethod(
                        progress, "setValue", 
                        Qt.QueuedConnection,
                        Q_ARG(int, 50)
                    )
                    
                    # 确保术语向量化
                    if success and hasattr(self.assistant.term_base, 'ensure_term_vectors'):
                        self.assistant.term_base.ensure_term_vectors()
                    
                    # 通知主线程
                    QMetaObject.invokeMethod(
                        self, "finish_add_term",
                        Qt.QueuedConnection,
                        Q_ARG(bool, success),
                        Q_ARG(str, source_term)
                    )
                except Exception as e:
                    print(f"添加术语出错: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # 通知主线程
                    QMetaObject.invokeMethod(
                        self, "finish_add_term",
                        Qt.QueuedConnection,
                        Q_ARG(bool, False),
                        Q_ARG(str, str(e))
                    )
            
            # 启动线程
            thread = threading.Thread(target=add_term_task)
            thread.daemon = True
            thread.start()
            
            # 更新进度条
            def update_progress():
                if progress.wasCanceled():
                    return
                
                current = progress.value()
                if current < 90 and thread.is_alive():
                    progress.setValue(current + 10)
                    QTimer.singleShot(300, update_progress)
                else:
                    progress.setValue(100)
                
            QTimer.singleShot(300, update_progress)
    
    @Slot(bool, str)
    def finish_add_term(self, success, message):
        """添加术语完成处理"""
        if success:
            QMessageBox.information(
                self,
                "添加成功",
                f"术语 '{message}' 已添加并向量化"
            )
            # 刷新术语列表
            self.load_term_list()
            
            # 设置术语列表选中新添加的术语
            for i in range(self.term_list.count()):
                if self.term_list.item(i).text() == message:
                    self.term_list.setCurrentRow(i)
                    break
        else:
            QMessageBox.warning(
                self,
                "添加失败",
                f"无法添加术语: {message}"
            )
    
    def edit_term(self):
        """编辑术语条目"""
        selected_items = self.term_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.i18n.translate("warning"), 
                               self.i18n.translate("select_term_first"))
            return
            
        term = selected_items[0].text()
        term_info = self.assistant.term_base.get_term_info(term)
        
        if not term_info:
            QMessageBox.warning(self, self.i18n.translate("warning"), 
                               self.i18n.translate("term_not_found"))
            return
        
        dialog = TermEditDialog(self, self.i18n)
        dialog.source_term_input.setText(term)
        dialog.source_term_input.setReadOnly(True)  # 不允许修改源术语
        
        # 填充第一个翻译
        if term_info.get('translations'):
            first_lang = list(term_info['translations'].keys())[0]
            first_trans = term_info['translations'][first_lang]
            dialog.source_lang_input.setText(term_info.get('source_language', 'zh'))
            dialog.target_lang_input.setText(first_lang)
            dialog.target_term_input.setText(first_trans)
        
        if dialog.exec():
            target_term = dialog.target_term_input.text().strip()
            target_lang = dialog.target_lang_input.text().strip() or 'en'
            
            if target_term:
                # 更新术语
                self.assistant.term_base.add_term(term, target_term, 
                                                term_info.get('source_language', 'zh'), 
                                                target_lang)
                self.assistant.term_base.save()
                
                # 刷新术语详情
                self.show_term_details()
            else:
                QMessageBox.warning(self, self.i18n.translate("warning"), 
                                   self.i18n.translate("translation_required"))
    
    def delete_term(self):
        """删除术语条目"""
        selected_items = self.term_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.i18n.translate("warning"), 
                               self.i18n.translate("select_term_first"))
            return
            
        term = selected_items[0].text()
        
        # 确认删除
        reply = QMessageBox.question(self, self.i18n.translate("confirm_delete"),
                                     self.i18n.translate("confirm_delete_term").format(term),
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 删除术语
            success = self.assistant.term_base.delete_term(term)
            if success:
                self.assistant.term_base.save()
                # 刷新列表
                self.load_term_list()
                # 清空详情
                self.term_details.clear()
            else:
                QMessageBox.warning(self, self.i18n.translate("warning"),
                                   self.i18n.translate("delete_failed"))
    
    def search_terms(self):
        """搜索术语"""
        query = self.search_input.text().strip()
        if not query:
            # 显示所有术语
            self.load_term_list()
            return
        
        try:
            # 使用简单文本搜索而不是向量搜索
            results = self._simple_search(query)
            
            # 显示结果
            self.term_list.clear()
            for term in results:
                self.term_list.addItem(term)
            
            # 显示结果数量
            if not results:
                QMessageBox.information(self, self.i18n.translate("search_results"),
                                       self.i18n.translate("no_matching_terms"))
        except Exception as e:
            print(f"搜索错误: {e}")
            import traceback
            traceback.print_exc()
            # 出错时显示所有术语
            self.load_term_list()
    
    def _simple_search(self, query):
        """简单文本搜索，不依赖向量"""
        results = []
        query_lower = query.lower()
        
        for term, term_info in self.assistant.term_base.terms.items():
            # 搜索源术语
            if query_lower in term.lower():
                results.append(term)
                continue
                
            # 搜索翻译
            found = False
            for lang, translation in term_info.get('translations', {}).items():
                if query_lower in translation.lower():
                    results.append(term)
                    found = True
                    break
                    
            if found:
                continue
        
        return results

    def ensure_signals_connected(self):
        """确保信号已连接，作为保障措施"""
        print("检查并确保术语面板信号已连接")
        self.signals_connected = False  # 强制重新连接
        self.connect_signals()
        
        # 测试点击按钮
        print("模拟点击导入按钮")
        self.import_btn.click()

    def diagnose_term_system(self):
        """诊断并尝试修复术语系统"""
        self.debug_label.setText("正在诊断术语系统...")
        
        dialog = QProgressDialog("正在诊断术语系统...", "取消", 0, 100, self)
        dialog.setWindowTitle("诊断中")
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setValue(10)
        dialog.show()
        
        def run_diagnosis():
            try:
                # 开始诊断
                if hasattr(self.assistant, 'diagnose_term_base'):
                    success = self.assistant.diagnose_term_base()
                else:
                    # 如果没有诊断函数，手动实现一个简化版诊断
                    print("手动检查术语库状态:")
                    
                    # 检查向量模型
                    if hasattr(self.assistant, 'term_vector_db'):
                        if not hasattr(self.assistant.term_vector_db, 'model') or self.assistant.term_vector_db.model is None:
                            if hasattr(self.assistant, 'vector_db') and hasattr(self.assistant.vector_db, 'model'):
                                self.assistant.term_vector_db.model = self.assistant.vector_db.model
                                print("已从主向量库复制模型到术语向量库")
                    
                    # 检查术语库初始化
                    if hasattr(self.assistant, 'term_base'):
                        if not hasattr(self.assistant.term_base, 'terms'):
                            self.assistant.term_base.terms = {}
                            print("已初始化空术语库")
                    success = True
                
                # 返回诊断结果
                QMetaObject.invokeMethod(
                    self, "diagnosis_complete", 
                    Qt.QueuedConnection,
                    Q_ARG(bool, success)
                )
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMetaObject.invokeMethod(
                    self, "diagnosis_complete", 
                    Qt.QueuedConnection,
                    Q_ARG(bool, False),
                    Q_ARG(str, str(e))
                )
        
        # 启动诊断线程
        thread = threading.Thread(target=run_diagnosis)
        thread.daemon = True
        thread.start()
        
        # 更新进度
        def update_progress():
            current = dialog.value()
            if current < 90 and thread.is_alive():
                dialog.setValue(current + 10)
                QTimer.singleShot(200, update_progress)
            else:
                dialog.setValue(100)
        
        QTimer.singleShot(200, update_progress)

    @Slot(bool, str)
    def diagnosis_complete(self, success, error_msg=""):
        """诊断完成处理"""
        if success:
            self.debug_label.setText("诊断完成: 系统正常")
            QMessageBox.information(self, "诊断结果", "术语系统诊断完成，系统功能正常。\n请尝试重新添加或导入术语。")
            
            # 重新加载术语列表
            self.load_term_list()
        else:
            self.debug_label.setText(f"诊断结果: 发现问题 - {error_msg}")
            QMessageBox.warning(self, "诊断结果", 
                              f"术语系统存在问题: {error_msg}\n建议重启应用程序或联系开发者。")

    def emergency_add_term(self):
        """应急添加术语功能 - 最简实现"""
        self.debug_label.setText("执行应急添加术语...")
        print("\n===== 应急添加术语 =====")
        
        try:
            # 直接获取当前时间作为测试术语
            import time
            term = f"测试术语_{int(time.time())}"
            definition = f"Test Term {int(time.time())}"
            
            print(f"添加术语: {term} -> {definition}")
            
            # 直接调用底层函数，而不是通过UI事件
            if hasattr(self.assistant, 'term_base') and self.assistant.term_base:
                result = self.assistant.term_base.add_term(term, definition)
                if result:
                    self.debug_label.setText(f"应急添加成功: {term}")
                    QMessageBox.information(self, "成功", f"已添加术语: {term}")
                    
                    # 手动保存
                    try:
                        self.assistant.term_base.save()
                        print("术语库已保存")
                    except Exception as e:
                        print(f"保存术语库失败: {e}")
                    
                    # 刷新列表
                    self.load_term_list()
                else:
                    self.debug_label.setText("应急添加失败")
                    QMessageBox.warning(self, "失败", "术语添加失败")
            else:
                self.debug_label.setText("错误: 术语库不存在")
                QMessageBox.critical(self, "错误", "术语库组件未初始化")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.debug_label.setText(f"错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"应急添加术语失败: {str(e)}")
        
        print("===== 应急添加完成 =====\n")

    def emergency_import(self):
        """应急导入术语 - 直接实现"""
        self.debug_label.setText("执行应急导入...")
        print("\n===== 应急导入术语 =====")
        
        try:
            # 同步选择文件
            filename, _ = QFileDialog.getOpenFileName(
                self, "选择术语文件", "", 
                "术语文件 (*.json *.csv *.tsv *.txt)"
            )
            
            if not filename:
                self.debug_label.setText("取消导入")
                return
            
            self.debug_label.setText(f"正在导入: {os.path.basename(filename)}")
            
            # 直接同步导入
            if hasattr(self.assistant, 'term_base') and self.assistant.term_base:
                # 直接同步调用，不使用线程
                success, message = self.assistant.term_base.import_terminology_file(filename)
                
                if success:
                    self.debug_label.setText(f"导入成功: {message}")
                    QMessageBox.information(self, "成功", f"导入成功: {message}")
                    self.load_term_list()
                else:
                    self.debug_label.setText(f"导入失败: {message}")
                    QMessageBox.warning(self, "失败", f"导入失败: {message}")
            else:
                self.debug_label.setText("错误: 术语库不存在")
                QMessageBox.critical(self, "错误", "术语库组件未初始化")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.debug_label.setText(f"错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"应急导入失败: {str(e)}")
        
        print("===== 应急导入完成 =====\n")

class TermEditDialog(QDialog):
    """术语编辑对话框"""
    
    def __init__(self, parent, i18n):
        super().__init__(parent)
        self.i18n = i18n
        self.setWindowTitle("添加专业术语")
        
        # 创建布局
        layout = QFormLayout(self)
        
        # 源术语输入 (中文)
        self.source_term_input = QLineEdit()
        self.source_term_input.setPlaceholderText("请输入中文术语")
        layout.addRow("中文术语:", self.source_term_input)
        
        # 源语言固定为中文
        self.source_lang_input = QLineEdit("zh")
        self.source_lang_input.setEnabled(False)  # 禁用编辑
        layout.addRow("源语言:", self.source_lang_input)
        
        # 目标术语输入 (外语定义)
        self.target_term_input = QLineEdit()
        self.target_term_input.setPlaceholderText("请输入对应的外语术语")
        layout.addRow("外语术语:", self.target_term_input)
        
        # 目标语言输入 (默认英语)
        self.target_lang_input = QLineEdit("en")
        layout.addRow("目标语言:", self.target_lang_input)
        
        # 添加说明标签
        note_label = QLabel("注意: 添加后将自动生成术语向量并保存")
        note_label.setStyleSheet("color: blue;")
        layout.addRow("", note_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("添加")
        cancel_button = QPushButton("取消")
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addRow("", button_layout)
        
        # 连接信号
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        # 设置对话框大小
        self.resize(450, 250)
        
        # 设置初始焦点
        self.source_term_input.setFocus() 