from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QCheckBox, QComboBox, QLabel, QFileDialog, QProgressBar)
from PySide6.QtCore import Qt, Slot
import threading
from PySide6.QtCore import QMetaObject, Q_ARG
from PySide6.QtCore import QTimer

class TranslationPanel(QWidget):
    """翻译面板"""
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.i18n = assistant.i18n
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 语言选择
        lang_layout = QHBoxLayout()
        
        self.source_lang = QComboBox()
        self.source_lang.addItems(["自动检测", "中文", "英文", "日文", "德文", "法文"])
        lang_layout.addWidget(QLabel(self.i18n.translate("source_language")))
        lang_layout.addWidget(self.source_lang)
        
        self.target_lang = QComboBox()
        self.target_lang.addItems(["英文", "中文", "日文", "德文", "法文"])
        lang_layout.addWidget(QLabel(self.i18n.translate("target_language")))
        lang_layout.addWidget(self.target_lang)
        
        layout.addLayout(lang_layout)
        
        # 原文输入区域
        layout.addWidget(QLabel(self.i18n.translate("source_text")))
        self.source_text = QTextEdit()
        # 添加文本变化监听，自动刷新术语
        self.source_text.textChanged.connect(self.on_source_text_changed)
        layout.addWidget(self.source_text)
        
        # 添加术语关键词展示区域
        term_layout = QVBoxLayout()
        term_header = QHBoxLayout()
        term_header.addWidget(QLabel("匹配到的术语关键词"))
        
        # 添加刷新按钮
        self.term_refresh_button = QPushButton("刷新术语")
        self.term_refresh_button.clicked.connect(self.refresh_matched_terms)
        term_header.addWidget(self.term_refresh_button)
        
        term_layout.addLayout(term_header)
        
        # 术语展示区域
        self.term_display = QTextEdit()
        self.term_display.setReadOnly(True)
        self.term_display.setMaximumHeight(80)  # 限制高度
        self.term_display.setPlaceholderText("输入文本，自动显示匹配到的术语")
        term_layout.addWidget(self.term_display)
        
        layout.addLayout(term_layout)
        
        # 选项区域
        options_layout = QHBoxLayout()
        
        self.use_terms = QCheckBox(self.i18n.translate("use_term_base"))
        self.use_terms.setChecked(True)  # 默认启用术语库
        options_layout.addWidget(self.use_terms)
        
        # 添加强制使用术语选项
        self.force_use_terms = QCheckBox("强制使用匹配术语")
        self.force_use_terms.setChecked(True)  # 默认启用强制使用术语
        options_layout.addWidget(self.force_use_terms)
        
        file_button = QPushButton(self.i18n.translate("import_file"))
        file_button.clicked.connect(self.import_file)
        options_layout.addWidget(file_button)
        
        layout.addLayout(options_layout)
        
        # 翻译按钮
        self.translate_button = QPushButton(self.i18n.translate("translate"))
        self.translate_button.clicked.connect(self.translate_text)
        layout.addWidget(self.translate_button)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 翻译结果区域
        layout.addWidget(QLabel(self.i18n.translate("translation_result")))
        self.target_text = QTextEdit()
        self.target_text.setReadOnly(True)
        layout.addWidget(self.target_text)
        
        # 导出按钮
        export_button = QPushButton(self.i18n.translate("export_translation"))
        export_button.clicked.connect(self.export_translation)
        layout.addWidget(export_button)
        
        # 设置自动刷新术语的定时器和标志
        self.term_refresh_timer = QTimer()
        self.term_refresh_timer.setSingleShot(True)
        self.term_refresh_timer.timeout.connect(self.refresh_matched_terms)
        self.is_text_changed = False
        
        self.setLayout(layout)
    
    def on_source_text_changed(self):
        """文本变化时自动刷新术语"""
        # 设置标志为已变化
        self.is_text_changed = True
        # 取消之前未执行的定时器（如果有）
        if self.term_refresh_timer.isActive():
            self.term_refresh_timer.stop()
        # 启动定时器，延迟1秒刷新术语，避免用户快速输入时频繁刷新
        self.term_refresh_timer.start(1000)  
    
    def refresh_matched_terms(self):
        """刷新匹配到的术语"""
        # 如果文本未变化，则不执行刷新
        if hasattr(self, 'is_text_changed') and not self.is_text_changed:
            return
        
        # 重置变化标志
        self.is_text_changed = False
        
        source_text = self.source_text.toPlainText()
        if not source_text.strip():
            self.term_display.setText("")
            return
        
        # 获取源语言和目标语言
        source_lang = self.source_lang.currentText()
        target_lang = self.target_lang.currentText()
        
        # 规范化语言代码
        if source_lang == "自动检测":
            source_lang = None
        elif source_lang == "中文":
            source_lang = "zh"
        elif source_lang == "英文":
            source_lang = "en"
        
        if target_lang == "中文":
            target_lang = "zh"
        elif target_lang == "英文":
            target_lang = "en"
        
        try:
            # 显示进度
            self.term_display.setText("正在匹配术语...")
            
            # 创建术语匹配线程
            class TermMatchThread(threading.Thread):
                def __init__(self, parent):
                    super().__init__()
                    self.parent = parent
                    self.daemon = True
                    self.matched_terms = []
                    self.error = None
                    
                def run(self):
                    try:
                        # 直接从translator获取术语匹配结果
                        translator = self.parent.assistant.translator
                        
                        # 优先使用translator中的方法
                        if hasattr(translator, '_find_matching_terms_in_text'):
                            # 获取术语库
                            terms = {}
                            if hasattr(translator, 'term_loader') and translator.term_loader:
                                if hasattr(translator.term_loader, 'terms'):
                                    terms = translator.term_loader.terms
                            elif hasattr(translator, 'terms'):
                                terms = translator.terms
                            
                            # 确保术语库不为空
                            if terms:
                                self.matched_terms = translator._find_matching_terms_in_text(
                                    source_text, terms, source_lang, target_lang
                                )
                            else:
                                # 尝试从AI引擎获取术语库
                                ai_engine = self.parent.assistant.ai_engine
                                if hasattr(ai_engine, 'terms') and ai_engine.terms:
                                    terms = ai_engine.terms
                                    
                                    # 使用translator或engine的匹配方法
                                    if hasattr(translator, '_find_matching_terms_in_text'):
                                        self.matched_terms = translator._find_matching_terms_in_text(
                                            source_text, terms, source_lang, target_lang
                                        )
                                    elif hasattr(ai_engine, '_find_matching_terms_in_text'):
                                        match_result = ai_engine._find_matching_terms_in_text(
                                            source_text, terms, source_lang, target_lang
                                        )
                                        
                                        # 处理可能的不同返回格式
                                        if isinstance(match_result, list):
                                            self.matched_terms = match_result
                                        elif isinstance(match_result, dict) and 'matched_terms' in match_result:
                                            # 旧格式返回字典，需要转换
                                            matched_dict = match_result['matched_terms']
                                            for term, info in matched_dict.items():
                                                term_info = info['term_info']
                                                self.matched_terms.append({
                                                    'source': term_info.get('source_term', term),
                                                    'target': term_info.get('target_term', ''),
                                                    'definition': term_info.get('definition', '')
                                                })
                    except Exception as e:
                        self.error = str(e)
                        import traceback
                        traceback.print_exc()
            
            # 启动术语匹配线程
            term_thread = TermMatchThread(self)
            term_thread.start()
            
            # 使用计时器定期检查线程是否完成
            def check_term_thread():
                if not term_thread.is_alive():
                    # 线程已完成
                    if term_thread.error:
                        self.term_display.setText(f"术语匹配出错：{term_thread.error}")
                    elif not term_thread.matched_terms:
                        self.term_display.setText("未匹配到术语")
                    else:
                        # 格式化显示匹配到的术语
                        term_text = "匹配到的术语关键词：\n"
                        for term in term_thread.matched_terms:
                            term_text += f"• {term['source']} => {term['target']}\n"
                        self.term_display.setText(term_text)
                        
                        # 保存匹配到的术语，供翻译使用
                        self.matched_terms = term_thread.matched_terms
                    timer.stop()
            
            timer = QTimer()
            timer.timeout.connect(check_term_thread)
            timer.start(100)  # 每100毫秒检查一次
            
        except Exception as e:
            self.term_display.setText(f"刷新术语出错：{str(e)}")
    
    def translate_text(self):
        """翻译文本"""
        source_text = self.source_text.toPlainText()
        if not source_text.strip():
            return
        
        # 获取源语言和目标语言
        source_lang = self.source_lang.currentText()
        target_lang = self.target_lang.currentText()
        
        # 规范化语言代码
        if source_lang == "自动检测":
            source_lang = None
        elif source_lang == "中文":
            source_lang = "zh"
        elif source_lang == "英文":
            source_lang = "en"
        
        if target_lang == "中文":
            target_lang = "zh"
        elif target_lang == "英文":
            target_lang = "en"
        
        # 应用术语库
        use_terms = self.use_terms.isChecked()
        force_use_terms = self.force_use_terms.isChecked()
        
        # 显示进度条
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setVisible(True)
        
        # 禁用翻译按钮
        self.translate_button.setEnabled(False)
        
        # 确保已刷新术语
        if not hasattr(self, 'matched_terms') or self.is_text_changed:
            self.refresh_matched_terms()
        
        # 创建翻译线程
        class TranslationThread(threading.Thread):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
                self.daemon = True
                self.result = None
                self.error = None
                
            def run(self):
                try:
                    # 准备术语和选项
                    matched_terms = getattr(self.parent, 'matched_terms', []) if use_terms else []
                    
                    # 构建翻译选项
                    translation_options = {
                        'use_termbase': use_terms,
                        'source_lang': source_lang,
                        'target_lang': target_lang,
                        'force_terms': force_use_terms
                    }
                    
                    # 如果启用了强制使用术语选项，则传递匹配到的术语列表
                    if force_use_terms and matched_terms:
                        translation_options['matched_terms'] = matched_terms
                    
                    # 使用提供的选项进行翻译
                    self.result = self.parent.assistant.translator.translate(
                        source_text, 
                        **translation_options
                    )
                except Exception as e:
                    self.error = str(e)
                    import traceback
                    traceback.print_exc()
        
        # 启动翻译线程
        translation_thread = TranslationThread(self)
        translation_thread.start()
        
        # 使用计时器定期检查线程是否完成
        def check_thread():
            if not translation_thread.is_alive():
                # 线程已完成
                if translation_thread.error:
                    error_msg = f"翻译错误：{translation_thread.error}"
                    self.target_text.setText(error_msg)
                    print(f"翻译失败: {translation_thread.error}")
                elif not translation_thread.result:
                    self.target_text.setText("翻译结果为空，可能是AI引擎未正确响应")
                    print("警告: 翻译结果为空")
                else:
                    self.target_text.setText(translation_thread.result)
                    print(f"翻译成功，生成了 {len(translation_thread.result)} 个字符")
                    
                # 恢复UI状态
                self.progress_bar.setVisible(False)
                self.translate_button.setEnabled(True)
                timer.stop()
        
        timer = QTimer()
        timer.timeout.connect(check_thread)
        timer.start(100)  # 每100毫秒检查一次
    
    def import_file(self):
        """导入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.translate("select_file_to_translate"),
            "",
            "Documents (*.txt *.md *.doc *.docx *.pdf)"
        )
        if not file_path:
            return
            
        # 这里应该有文件读取和预处理的代码
        # 简化处理，仅支持文本文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.source_text.setText(content)
        except Exception as e:
            self.assistant.main_window.statusBar().showMessage(
                f"{self.i18n.translate('file_read_error')}: {str(e)}", 3000
            )
    
    def export_translation(self):
        """导出翻译结果"""
        translation = self.target_text.toPlainText()
        if not translation:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.translate("save_translation"),
            "",
            "Text files (*.txt)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(translation)
            self.assistant.main_window.statusBar().showMessage(
                self.i18n.translate("translation_saved"), 3000
            )
        except Exception as e:
            self.assistant.main_window.statusBar().showMessage(
                f"{self.i18n.translate('save_error')}: {str(e)}", 3000
            )
    
    @Slot(str)
    def set_translation_result(self, translation):
        """设置翻译结果"""
        self.target_text.setText(translation)
    
    @Slot(str)
    def show_error(self, error_msg):
        """显示错误信息"""
        self.target_text.setText(f"翻译错误：{error_msg}")
    
    @Slot()
    def translation_completed(self):
        """翻译完成后更新UI状态"""
        self.progress_bar.setVisible(False)
        self.translate_button.setEnabled(True)

    def on_source_text_changed(self):
        """文本变化时自动刷新术语"""
        # 设置标志为已变化
        self.is_text_changed = True
        # 取消之前未执行的定时器（如果有）
        if self.term_refresh_timer.isActive():
            self.term_refresh_timer.stop()
        # 启动定时器，延迟1秒刷新术语，避免用户快速输入时频繁刷新
        self.term_refresh_timer.start(1000)  

    def refresh_matched_terms(self):
        """刷新匹配到的术语"""
        # 如果文本未变化，则不执行刷新
        if hasattr(self, 'is_text_changed') and not self.is_text_changed:
            return
        
        # 重置变化标志
        self.is_text_changed = False
        
        source_text = self.source_text.toPlainText()
        if not source_text.strip():
            self.term_display.setText("")
            return
        
        # 获取源语言和目标语言
        source_lang = self.source_lang.currentText()
        target_lang = self.target_lang.currentText()
        
        # 规范化语言代码
        if source_lang == "自动检测":
            source_lang = None
        elif source_lang == "中文":
            source_lang = "zh"
        elif source_lang == "英文":
            source_lang = "en"
        
        if target_lang == "中文":
            target_lang = "zh"
        elif target_lang == "英文":
            target_lang = "en"
        
        try:
            # 显示进度
            self.term_display.setText("正在匹配术语...")
            
            # 创建术语匹配线程
            class TermMatchThread(threading.Thread):
                def __init__(self, parent):
                    super().__init__()
                    self.parent = parent
                    self.daemon = True
                    self.matched_terms = []
                    self.error = None
                    
                def run(self):
                    try:
                        # 直接从translator获取术语匹配结果
                        translator = self.parent.assistant.translator
                        
                        # 优先使用translator中的方法
                        if hasattr(translator, '_find_matching_terms_in_text'):
                            # 获取术语库
                            terms = {}
                            if hasattr(translator, 'term_loader') and translator.term_loader:
                                if hasattr(translator.term_loader, 'terms'):
                                    terms = translator.term_loader.terms
                            elif hasattr(translator, 'terms'):
                                terms = translator.terms
                            
                            # 确保术语库不为空
                            if terms:
                                self.matched_terms = translator._find_matching_terms_in_text(
                                    source_text, terms, source_lang, target_lang
                                )
                            else:
                                # 尝试从AI引擎获取术语库
                                ai_engine = self.parent.assistant.ai_engine
                                if hasattr(ai_engine, 'terms') and ai_engine.terms:
                                    terms = ai_engine.terms
                                    
                                    # 使用translator或engine的匹配方法
                                    if hasattr(translator, '_find_matching_terms_in_text'):
                                        self.matched_terms = translator._find_matching_terms_in_text(
                                            source_text, terms, source_lang, target_lang
                                        )
                                    elif hasattr(ai_engine, '_find_matching_terms_in_text'):
                                        match_result = ai_engine._find_matching_terms_in_text(
                                            source_text, terms, source_lang, target_lang
                                        )
                                        
                                        # 处理可能的不同返回格式
                                        if isinstance(match_result, list):
                                            self.matched_terms = match_result
                                        elif isinstance(match_result, dict) and 'matched_terms' in match_result:
                                            # 旧格式返回字典，需要转换
                                            matched_dict = match_result['matched_terms']
                                            for term, info in matched_dict.items():
                                                term_info = info['term_info']
                                                self.matched_terms.append({
                                                    'source': term_info.get('source_term', term),
                                                    'target': term_info.get('target_term', ''),
                                                    'definition': term_info.get('definition', '')
                                                })
                    except Exception as e:
                        self.error = str(e)
                        import traceback
                        traceback.print_exc()
            
            # 启动术语匹配线程
            term_thread = TermMatchThread(self)
            term_thread.start()
            
            # 使用计时器定期检查线程是否完成
            def check_term_thread():
                if not term_thread.is_alive():
                    # 线程已完成
                    if term_thread.error:
                        self.term_display.setText(f"术语匹配出错：{term_thread.error}")
                    elif not term_thread.matched_terms:
                        self.term_display.setText("未匹配到术语")
                    else:
                        # 格式化显示匹配到的术语
                        term_text = "匹配到的术语关键词：\n"
                        for term in term_thread.matched_terms:
                            term_text += f"• {term['source']} => {term['target']}\n"
                        self.term_display.setText(term_text)
                        
                        # 保存匹配到的术语，供翻译使用
                        self.matched_terms = term_thread.matched_terms
                    timer.stop()
            
            timer = QTimer()
            timer.timeout.connect(check_term_thread)
            timer.start(100)  # 每100毫秒检查一次
            
        except Exception as e:
            self.term_display.setText(f"刷新术语出错：{str(e)}")

    def translate_text(self):
        """翻译文本"""
        source_text = self.source_text.toPlainText()
        if not source_text.strip():
            return
        
        # 获取源语言和目标语言
        source_lang = self.source_lang.currentText()
        target_lang = self.target_lang.currentText()
        
        # 规范化语言代码
        if source_lang == "自动检测":
            source_lang = None
        elif source_lang == "中文":
            source_lang = "zh"
        elif source_lang == "英文":
            source_lang = "en"
        
        if target_lang == "中文":
            target_lang = "zh"
        elif target_lang == "英文":
            target_lang = "en"
        
        # 应用术语库
        use_terms = self.use_terms.isChecked()
        force_use_terms = self.force_use_terms.isChecked()
        
        # 显示进度条
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setVisible(True)
        
        # 禁用翻译按钮
        self.translate_button.setEnabled(False)
        
        # 确保已刷新术语
        if not hasattr(self, 'matched_terms') or self.is_text_changed:
            self.refresh_matched_terms()
        
        # 创建翻译线程
        class TranslationThread(threading.Thread):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
                self.daemon = True
                self.result = None
                self.error = None
                
            def run(self):
                try:
                    # 准备术语和选项
                    matched_terms = getattr(self.parent, 'matched_terms', []) if use_terms else []
                    
                    # 构建翻译选项
                    translation_options = {
                        'use_termbase': use_terms,
                        'source_lang': source_lang,
                        'target_lang': target_lang,
                        'force_terms': force_use_terms
                    }
                    
                    # 如果启用了强制使用术语选项，则传递匹配到的术语列表
                    if force_use_terms and matched_terms:
                        translation_options['matched_terms'] = matched_terms
                    
                    # 使用提供的选项进行翻译
                    self.result = self.parent.assistant.translator.translate(
                        source_text, 
                        **translation_options
                    )
                except Exception as e:
                    self.error = str(e)
                    import traceback
                    traceback.print_exc()
        
        # 启动翻译线程
        translation_thread = TranslationThread(self)
        translation_thread.start()
        
        # 使用计时器定期检查线程是否完成
        def check_thread():
            if not translation_thread.is_alive():
                # 线程已完成
                if translation_thread.error:
                    error_msg = f"翻译错误：{translation_thread.error}"
                    self.target_text.setText(error_msg)
                    print(f"翻译失败: {translation_thread.error}")
                elif not translation_thread.result:
                    self.target_text.setText("翻译结果为空，可能是AI引擎未正确响应")
                    print("警告: 翻译结果为空")
                else:
                    self.target_text.setText(translation_thread.result)
                    print(f"翻译成功，生成了 {len(translation_thread.result)} 个字符")
                    
                # 恢复UI状态
                self.progress_bar.setVisible(False)
                self.translate_button.setEnabled(True)
                timer.stop()
        
        timer = QTimer()
        timer.timeout.connect(check_thread)
        timer.start(100)  # 每100毫秒检查一次 