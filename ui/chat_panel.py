from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTextEdit, QCheckBox, QSplitter, QLabel, QProgressBar, QMessageBox, QProgressDialog, QScrollArea, QTextBrowser)
from PySide6.QtCore import Qt, QEvent, Signal, QTimer, QMetaObject, Q_ARG
from PySide6.QtGui import QTextCursor
import threading
import jieba.analyse
import os
import requests
import zipfile
import random
from datetime import datetime
import time
import re

class ChatPanel(QWidget):
    """聊天对话面板"""
    
    # 定义所需的信号
    progressUpdated = Signal(int)  # 进度更新信号
    messageReceived = Signal(str, bool)  # 消息接收信号 (文本, 是否用户发送)
    removeThinkingIndicator = Signal()  # 移除思考指示器信号
    delayHideProgressBar = Signal()  # 延迟隐藏进度条信号
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.i18n = assistant.i18n
        self.settings = assistant.settings
        
        # 检查知识库状态
        if hasattr(assistant, 'knowledge_base'):
            try:
                kb_items = assistant.knowledge_base.list_items()
                print(f"[DEBUG] 知识库初始化状态: 已加载 {len(kb_items)} 条目")
            except Exception as e:
                print(f"[ERROR] 知识库检查失败: {e}")
        else:
            print("[WARNING] 应用程序未初始化知识库组件")
        
        # 移除语音模式
        # self.speech_mode = False  # 直接禁用语音模式
        
        self.chat_history = []  # 格式化为[{'role': 'user'/'assistant', 'content': '消息内容'}]
        self.query_cache = {}  # 查询缓存: {查询: {知识上下文, 回复}}
        self.init_ui()
        
        # 安装事件过滤器，监听回车键
        self.chat_input.installEventFilter(self)
        
        # 连接信号 - 修复信号连接
        self.progressUpdated.connect(self.updateProgress)
        self.messageReceived.connect(self.add_message)
        
        # 使用Lambda表达式不带参数 - 修复信号连接问题
        self.removeThinkingIndicator.connect(self.remove_thinking_indicator)
        
        self.delayHideProgressBar.connect(self.hideProgressBarDelayed)
        
        # 在__init__方法末尾添加
        print("ChatPanel初始化完成")
        # print(f"语音模式状态: {self.speech_mode}")  # 移除语音模式状态打印
        print(f"助手实例类型: {type(self.assistant).__name__}")

        # 检查助手对象的方法
        if self.assistant:
            response_methods = []
            for method_name in ['get_response', 'generate_response', 'chat', 'respond', 'answer']:
                if hasattr(self.assistant, method_name):
                    response_methods.append(method_name)
            print(f"助手对象存在的响应方法: {response_methods}")
        else:
            print("警告: 助手对象为空")
        
        # 在初始化末尾调用调试方法
        self.debug_assistant_methods()
        
    def init_ui(self):
        """初始化UI界面，确保所有标签使用中文"""
        layout = QVBoxLayout()
        
        # 聊天历史显示区域
        self.chat_display_container = QWidget()
        self.chat_history_layout = QVBoxLayout(self.chat_display_container)
        self.chat_history_layout.setAlignment(Qt.AlignTop)
        self.chat_history_layout.setSpacing(10)  # 减少消息间距
        
        # 放置聊天历史的滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.chat_display_container)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 美化滚动区域 - 简化样式
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: #ffffff; }
            QScrollBar:vertical { background: #f0f0f0; width: 8px; margin: 0px; }
            QScrollBar::handle:vertical { background: #c0c0c0; min-height: 20px; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        # 聊天设置区域
        settings_layout = QHBoxLayout()
        
        # 多轮对话开关
        self.multi_turn_switch = QCheckBox()
        multi_turn_value = self.settings.get('enable_multi_turn', False)
        self.multi_turn_switch.setChecked(multi_turn_value)
        self.multi_turn_switch.stateChanged.connect(self.toggle_multi_turn)
        
        # 使用中文标签显示多轮对话文字
        multi_turn_label = QLabel("多轮对话")
        multi_turn_label.setStyleSheet("color: #333333;")
        
        # 组合成水平布局
        multi_turn_layout = QHBoxLayout()
        multi_turn_layout.addWidget(self.multi_turn_switch)
        multi_turn_layout.addWidget(multi_turn_label)
        multi_turn_layout.addStretch()
        
        settings_layout.addLayout(multi_turn_layout)
        
        # 知识库辅助开关 - 修复开关状态问题
        self.knowledge_switch = QCheckBox()
        knowledge_value = True  # 默认启用
        try:
            # 尝试从设置中获取，但确保默认为True
            knowledge_value = bool(self.settings.get('enable_knowledge', True))
        except:
            knowledge_value = True
        
        self.knowledge_switch.setChecked(knowledge_value)
        # 连接到固定名称的方法
        self.knowledge_switch.stateChanged.connect(self.toggle_knowledge)
        print(f"[DEBUG] 知识库辅助开关初始状态设置为: {'启用' if knowledge_value else '禁用'}")
        
        # 确保使用中文标签
        knowledge_label = QLabel("知识库辅助")
        knowledge_label.setStyleSheet("color: #333333;")
        
        # 组合成水平布局
        knowledge_layout = QHBoxLayout()
        knowledge_layout.addWidget(self.knowledge_switch)
        knowledge_layout.addWidget(knowledge_label)
        knowledge_layout.addStretch()
        
        settings_layout.addLayout(knowledge_layout)
        
        # 添加记忆状态指示器 - 直接使用中文
        self.memory_indicator = QLabel()
        memory_state = "记忆已启用" if multi_turn_value else "记忆已禁用"
        icon = "💭" if multi_turn_value else "🔄"
        self.memory_indicator.setText(f"{icon} {memory_state}")
        self.memory_indicator.setStyleSheet(f"color: {'#4CAF50' if multi_turn_value else '#757575'};")
        settings_layout.addWidget(self.memory_indicator)
        
        settings_layout.addStretch()
        
        # 清空聊天按钮 - 直接使用中文
        self.clear_button = QPushButton("清空对话")
        self.clear_button.setStyleSheet("background-color: #f44336; color: white; padding: 5px 15px; border-radius: 4px;")
        self.clear_button.clicked.connect(self.clear_chat)
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar {border: 1px solid #CCCCCC; border-radius: 4px; text-align: center;} "
                                      "QProgressBar::chunk {background-color: #4CAF50; width: 1px;}")
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("在此输入您的消息...")
        self.chat_input.setFixedHeight(80)
        self.chat_input.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 4px; padding: 5px;")
        input_layout.addWidget(self.chat_input)
        
        self.send_button = QPushButton("发送")
        self.send_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 15px; border-radius: 4px;")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        # 添加清空按钮到底部布局
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.clear_button)
        
        # 布局组装
        layout.addWidget(scroll_area)
        layout.addLayout(settings_layout)
        layout.addWidget(self.progress_bar)
        layout.addLayout(input_layout)
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)

        # 在UI初始化完成后调用诊断
        QTimer.singleShot(500, self.debug_knowledge_system)  # 延迟调用，确保所有组件初始化完成

    def add_message(self, message, is_user=False):
        """添加消息到聊天历史"""
        # 设置发送者名称为中文
        sender = "我" if is_user else "松瓷机电AI助手"
        
        # 添加到消息显示区域
        self.add_message_to_display(sender, message)
    
    def add_thinking_indicator(self):
        """添加思考中指示器，返回一个用于标识的ID"""
        thinking_id = random.randint(1000, 9999)
        
        # 保存当前思考ID
        self.current_thinking_id = thinking_id
        
        # 添加思考中的指示
        self.chat_display.append(f"AI (思考中...{thinking_id})")
        self.chat_display.ensureCursorVisible()
        
        return thinking_id
    
    def remove_thinking_indicator(self):
        """移除思考指示器"""
        if hasattr(self, 'current_thinking_widget') and self.current_thinking_widget:
            try:
                # 直接在当前线程中移除指示器，而不调用不存在的方法
                self.chat_history_layout.removeWidget(self.current_thinking_widget)
                self.current_thinking_widget.deleteLater()
                self.current_thinking_widget = None
            except Exception as e:
                print(f"移除思考指示器时出错: {e}")

    def updateProgress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
        # 根据进度显示或隐藏
        if value >= 100 or value <= 0:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
    
    def send_message(self):
        """发送消息"""
        message = self.chat_input.toPlainText().strip()
        if not message:
            return
        
        # 清空输入框
        self.chat_input.clear()
        
        # 禁用发送按钮
        self.send_button.setEnabled(False)
        
        # 添加用户消息，确保使用中文"我"作为发送者
        self.add_message(message, is_user=True)
        
        # 添加到聊天历史
        self.chat_history.append({"role": "user", "content": message})
        
        # 显示进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 创建思考指示器占位消息
        thinking_widget = QWidget()
        thinking_layout = QVBoxLayout(thinking_widget)
        thinking_layout.setContentsMargins(5, 5, 5, 5)
        
        # 思考中标签 - 确保使用中文
        thinking_label = QLabel("松瓷机电AI助手 思考中...")
        thinking_label.setStyleSheet("font-weight: bold; color: #555555;")
        thinking_layout.addWidget(thinking_label)
        
        # 添加到聊天历史
        self.chat_history_layout.addWidget(thinking_widget)
        self.current_thinking_widget = thinking_widget
        
        # 滚动到底部
        self.scroll_to_bottom()
        
        # 在后台线程中获取回复
        thread = threading.Thread(target=self.get_reply_thread, args=(message,))
        thread.daemon = True
        thread.start()

    def get_reply_thread(self, message):
        """在线程中获取AI回复，改进知识库检索流程"""
        try:
            # 检查是否使用多轮对话
            multi_turn = self.multi_turn_switch.isChecked()
            
            # 直接从开关获取知识库状态
            use_knowledge = self.knowledge_switch.isChecked()
            
            print(f"[DEBUG] 开始处理问题: {message}")
            print(f"[DEBUG] 知识库辅助当前状态: {'启用' if use_knowledge else '禁用'}")
            print(f"[DEBUG] 知识库是否可用: {hasattr(self.assistant, 'knowledge_base')}")
            
            # 获取格式化的聊天历史
            history = self.format_chat_history() if multi_turn else []
            
            print(f"开始获取AI回复，知识库辅助模式: {use_knowledge}")
            start_time = time.time()
            
            # 处理知识库辅助
            knowledge_text = None
            if use_knowledge and hasattr(self.assistant, 'knowledge_base'):
                try:
                    print("[DEBUG] 准备使用知识库辅助回答")
                    print(f"[DEBUG] 正在搜索与问题相关的知识: {message}")
                    
                    # 显式调用知识库搜索，增加debug日志
                    knowledge_base = self.assistant.knowledge_base
                    print(f"[DEBUG] 知识库类型: {type(knowledge_base).__name__}")
                    print(f"[DEBUG] 知识库方法: {[m for m in dir(knowledge_base) if callable(getattr(knowledge_base, m)) and not m.startswith('_')]}")
                    
                    # 调用搜索方法
                    knowledge_results = knowledge_base.search(message, top_k=15)
                    
                    # 处理搜索结果
                    if knowledge_results and len(knowledge_results) > 0:
                        knowledge_text = self.process_knowledge_results(knowledge_results, message)
                        
                        if knowledge_text:
                            print("[INFO] 使用知识库辅助回答问题")
                            
                            # 优先使用chat_with_knowledge方法
                            if hasattr(self.assistant, 'chat_with_knowledge'):
                                reply = self.assistant.chat_with_knowledge(message, knowledge_text)
                            else:
                                # 构建增强提示
                                knowledge_prompt = (
                                    f"我将为你提供一些相关知识，请基于这些知识来回答用户的问题。\n\n"
                                    f"相关知识：\n{knowledge_text}\n\n"
                                    f"用户问题: {message}\n\n"
                                    f"请使用Markdown格式组织你的回答，确保答案清晰、结构良好。"
                                    f"如果知识库中包含足够信息，请直接基于知识回答。"
                                    f"如果知识库内容不足，可以适当补充相关内容。"
                                )
                                reply = self.assistant.chat(knowledge_prompt)
                        else:
                            print("[INFO] 搜索结果质量不足，回退到普通模式")
                            reply = self.assistant.chat(message)
                    else:
                        print("[INFO] 未找到相关知识条目，回退到普通模式")
                        reply = self.assistant.chat(message)
                except Exception as e:
                    # 出错时回退到普通模式
                    print(f"[ERROR] 知识库搜索失败: {e}")
                    import traceback
                    traceback.print_exc()
                    reply = self.assistant.chat(message)
            else:
                # 普通模式回答
                print("[INFO] 使用普通模式回答问题")
                reply = self.assistant.chat(message)
            
            # 清理回复格式 - 只保留最终回答部分
            reply = self.clean_ai_response(reply)
            
            # 计算消息长度和处理时间
            end_time = time.time()
            chars = len(reply)
            elapsed = end_time - start_time
            print(f"获取AI回复: {chars} 字符，耗时 {elapsed:.2f} 秒")
            
            # 使用信号更新UI
            self.removeThinkingIndicator.emit()
            self.messageReceived.emit(reply, False)
            
            # 在主线程中执行UI操作
            QMetaObject.invokeMethod(self.send_button, "setEnabled", 
                                    Qt.QueuedConnection,
                                    Q_ARG(bool, True))
            self.delayHideProgressBar.emit()
            
            # 添加到聊天历史
            if multi_turn:
                self.chat_history.append({"role": "assistant", "content": reply})
        
        except Exception as e:
            # 处理错误
            import traceback
            traceback.print_exc()
            
            error_msg = f"获取AI回复失败: {str(e)}"
            print(error_msg)
            
            # 在主线程中更新UI
            self.removeThinkingIndicator.emit()
            self.messageReceived.emit(error_msg, False)
            QMetaObject.invokeMethod(self.send_button, "setEnabled", 
                                    Qt.QueuedConnection,
                                    Q_ARG(bool, True))
            self.delayHideProgressBar.emit()

    def clean_ai_response(self, response):
        """彻底清理AI回复中的所有角色标签和格式前缀"""
        if not response:
            return ""
        
        # 添加处理assistantapatite这类混合标签的逻辑
        if "assistantapatite" in response:
            parts = response.split("assistantapatite", 1)
            if len(parts) > 1:
                response = parts[1].strip()
                print("[DEBUG] 已提取assistantapatite标签后的内容")
        
        # 处理solver标签 - 添加solver标签处理
        elif "solver" in response:
            parts = response.split("solver", 1)
            if len(parts) > 1:
                response = parts[1].strip()
                print("[DEBUG] 已提取solver标签后的内容")
        
        # 首先处理特定的输出标签
        # 优先处理answer标签
        elif "answer" in response:
            parts = response.split("answer", 1)
            if len(parts) > 1:
                response = parts[1].strip()
                print("[DEBUG] 已提取answer标签后的内容")
        
        # 其次处理cerer标签
        elif "cerer" in response:
            parts = response.split("cerer", 1)
            if len(parts) > 1:
                response = parts[1].strip()
                print("[DEBUG] 已提取cerer标签后的内容")
        
        # 处理assistant标签
        elif "assistant" in response and not response.startswith("assistantapatite"):
            parts = response.split("assistant", 1)
            if len(parts) > 1:
                response = parts[1].strip()
                print("[DEBUG] 已提取assistant标签后的内容")
        
        # 再处理可能存在的顶层结构
        if "\nuser" in response:
            # 分割找到最后一个user标签
            parts = response.split("\nuser")
            if len(parts) > 1:
                # 取最后一部分
                response = parts[-1].strip()
        
        # 如果开头还有user标记
        if response.startswith("user"):
            response = response[4:].strip()
        
        # 移除其他可能的前缀
        for prefix in ["AI:", "AI：", "助手:", "助手：", "system"]:
            if response.lower().startswith(prefix.lower()):
                response = response[len(prefix):].strip()
        
        # 移除可能的引导语
        common_intros = [
            "根据提供的知识",
            "根据给出的信息",
            "根据上述知识",
            "基于提供的知识",
            "基于相关知识"
        ]
        
        for intro in common_intros:
            if response.startswith(intro):
                # 找到第一个完整的句子结束位置
                pos = response.find("，", len(intro))
                if pos > 0:
                    response = response[pos+1:].strip()
        
        return response.strip()

    def update_with_reply(self, reply):
        """接收AI回复并更新UI（用于线程间调用）"""
        # 移除思考指示（如果有）
        if hasattr(self, 'thinking_indicator_id'):
            self.remove_thinking_indicator(self.thinking_indicator_id)
        
        # 添加AI回复到聊天记录
        self.add_message(reply, is_user=False)
        
        # 重新启用发送按钮
        self.send_button.setEnabled(True)
    
    def add_message_to_display(self, sender, message):
        """添加消息到显示区域，支持Markdown格式显示"""
        # 创建消息组件
        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        message_layout.setContentsMargins(5, 3, 5, 3)
        
        # 设置发送者名称
        is_user = sender.lower() in ["user", "我"]
        display_sender = "我：" if is_user else "AI："
        
        # 清理消息内容，移除可能的角色标记
        clean_message = message
        for prefix in ["system", "user", "assistant", "cerer"]:
            if clean_message.startswith(prefix):
                clean_message = clean_message[len(prefix):].strip()
        
        # 创建标签显示消息
        message_label = QLabel()
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_label.setWordWrap(True)
        
        # 检测是否包含可能的Markdown内容
        has_markdown = any(marker in clean_message for marker in 
                          ["#", "```", "*", "_", ">", "- ", "1. ", "|", "![", "["])
        
        if not is_user and has_markdown and hasattr(self, 'render_markdown'):
            # 尝试使用Markdown渲染
            try:
                rendered_html = self.render_markdown(clean_message)
                message_label.setText(f"{display_sender}\n{rendered_html}")
                message_label.setTextFormat(Qt.RichText)
            except:
                # 如果Markdown渲染失败，使用普通文本
                message_label.setText(f"{display_sender} {clean_message}")
        else:
            # 用户消息或无Markdown的AI消息
            message_label.setText(f"{display_sender} {clean_message}")
        
        message_label.setStyleSheet("color: #000000; font-family: 'Microsoft YaHei';")
        
        message_layout.addWidget(message_label)
        self.chat_history_layout.addWidget(message_widget)
        self.scroll_to_bottom()

    def render_markdown(self, text):
        """增强的Markdown渲染为HTML"""
        html = text
        
        # 处理代码块
        code_block_pattern = r'```(.+?)```'
        html = re.sub(code_block_pattern, r'<pre style="background-color:#f5f5f5;padding:10px;border-radius:5px;overflow:auto;"><code>\1</code></pre>', html, flags=re.DOTALL)
        
        # 处理标题
        for i in range(6, 0, -1):
            pattern = r'^#{' + str(i) + r'}\s+(.+?)$'
            replacement = r'<h' + str(i) + r' style="color:#333;border-bottom:1px solid #eee;">\1</h' + str(i) + r'>'
            html = re.sub(pattern, replacement, html, flags=re.MULTILINE)
        
        # 处理粗体
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        
        # 处理斜体
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)
        
        # 处理列表
        html = re.sub(r'^- (.+?)$', r'<ul style="margin:0;padding-left:20px;"><li>\1</li></ul>', html, flags=re.MULTILINE)
        html = re.sub(r'^(\d+)\. (.+?)$', r'<ol start="\1" style="margin:0;padding-left:20px;"><li>\2</li></ol>', html, flags=re.MULTILINE)
        
        # 处理换行
        html = html.replace('\n\n', '<br><br>')
        html = re.sub(r'(?<!\>)\n(?!\<)', '<br>', html)
        
        return html
    
    def clear_chat(self):
        """清空聊天记录"""
        # 清除聊天历史容器中的所有消息组件
        while self.chat_history_layout.count():
            item = self.chat_history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 清空聊天历史数组
        self.chat_history = [] 
        
        # 重置进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
    
    def eventFilter(self, watched, event):
        """事件过滤器，处理回车键发送消息"""
        if watched == self.chat_input and event.type() == QEvent.KeyPress:
            key_event = event
            
            # 检测是否为回车键，且没有按下Shift或Ctrl
            if (key_event.key() == Qt.Key_Return or key_event.key() == Qt.Key_Enter) and \
               not key_event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # 拦截回车键，触发发送
                self.send_message()
                return True
            
            # Shift+Enter插入换行
            if (key_event.key() == Qt.Key_Return or key_event.key() == Qt.Key_Enter) and \
               key_event.modifiers() & Qt.ShiftModifier:
                # 正常处理Shift+Enter
                return False
        
        # 其他事件正常处理
        return super().eventFilter(watched, event) 

    def hideProgressBarDelayed(self):
        """在主线程中延迟隐藏进度条"""
        # 创建一个单次计时器，在主线程中操作
        QTimer.singleShot(1000, lambda: self.progressUpdated.emit(0)) 

    def format_chat_history(self):
        """格式化聊天历史，用于传递给AI引擎"""
        return self.chat_history 

    def toggle_multi_turn(self, state):
        """切换多轮对话模式"""
        is_enabled = (state == Qt.Checked)
        self.assistant.settings.set('enable_multi_turn', is_enabled)
        
        # 更新内存指示器
        self.update_memory_indicator(is_enabled)
        
        # 如果关闭多轮对话，清空历史
        if not is_enabled:
            self.chat_history.clear()
        
        print(f"多轮对话模式: {'开启' if is_enabled else '关闭'}")

    def get_current_time(self):
        """获取当前时间格式化字符串"""
        return datetime.now().strftime("%H:%M:%S") 

    def debug_assistant_methods(self):
        """调试助手对象可用的方法"""
        if not self.assistant:
            print("助手对象为空")
            return
        
        print("\n======= AIAssistant可用的方法 =======")
        
        # 记录可能的生成方法
        generation_methods = []
        
        for method_name in dir(self.assistant):
            # 跳过特殊方法和非公开方法
            if method_name.startswith('__'):
                continue
            
            # 获取方法
            method = getattr(self.assistant, method_name)
            if callable(method):
                try:
                    # 获取方法签名
                    import inspect
                    signature = inspect.signature(method)
                    
                    # 可能的生成方法应该接受一个参数(通常是文本输入)
                    if len(signature.parameters) == 1:
                        param_name = list(signature.parameters.keys())[0]
                        # 如果参数名称暗示输入文本，可能是生成方法
                        if param_name.lower() in ['text', 'prompt', 'query', 'message', 'input', 'question']:
                            generation_methods.append(method_name)
                            print(f"  - {method_name}{signature} [可能的生成方法]")
                        else:
                            print(f"  - {method_name}{signature}")
                    else:
                        print(f"  - {method_name}{signature}")
                except:
                    print(f"  - {method_name}()")
        
        # 打印可能的生成方法列表
        if generation_methods:
            print(f"\n潜在的生成方法: {', '.join(generation_methods)}")
        else:
            print("\n未找到明显的生成方法")
        
        # 尝试检查assistant的一些关键属性
        print("\n======= AIAssistant关键属性 =======")
        for attr_name in ['model', 'llm', 'engine', 'generator', 'model_manager', 'tokenizer']:
            if hasattr(self.assistant, attr_name):
                attr = getattr(self.assistant, attr_name)
                print(f"  - {attr_name}: {type(attr).__name__}")
                
                # 进一步检查这个属性的方法
                if attr_name in ['engine', 'model_manager']:
                    print(f"\n------- {attr_name}的方法 -------")
                    for m_name in dir(attr):
                        if not m_name.startswith('__'):
                            m = getattr(attr, m_name)
                            if callable(m):
                                try:
                                    sig = inspect.signature(m)
                                    print(f"  - {m_name}{sig}")
                                except:
                                    print(f"  - {m_name}()")
        
        print("===============================\n") 

    def scroll_to_bottom(self):
        """滚动到聊天记录底部"""
        # 找到滚动区域 (父级的 QScrollArea)
        scroll_area = None
        for parent in self.chat_display_container.parentWidget().findChildren(QScrollArea):
            scroll_area = parent
            break
        
        if scroll_area:
            # 滚动到最大垂直位置
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum()) 

    def update_memory_indicator(self, enabled):
        """更新内存状态指示器，直接使用中文"""
        if enabled:
            self.memory_indicator.setText("💭 记忆已启用")
            self.memory_indicator.setStyleSheet("color: #4CAF50;")
        else:
            self.memory_indicator.setText("🔄 记忆已禁用")
            self.memory_indicator.setStyleSheet("color: #757575;")

    def toggle_knowledge(self, state):
        """切换知识库辅助模式，修复状态保存和显示问题"""
        # 直接从开关控件获取当前状态，而不是依赖参数
        is_enabled = self.knowledge_switch.isChecked()
        
        # 记录确切的状态
        print(f"[DEBUG] 知识库辅助模式已切换为: {'启用' if is_enabled else '禁用'}")
        print(f"[DEBUG] 开关状态: {self.knowledge_switch.isChecked()}")
        
        # 确保设置被正确保存
        try:
            self.assistant.settings.set('enable_knowledge', is_enabled)
            # 直接访问设置字典以验证
            if hasattr(self.assistant.settings, '_settings'):
                print(f"[DEBUG] 设置值: {self.assistant.settings._settings.get('enable_knowledge')}")
        except Exception as e:
            print(f"[ERROR] 无法保存知识库设置: {e}")
        
        # 更新状态显示
        knowledge_status = "知识辅助已启用" if is_enabled else "知识辅助已禁用"
        print(f"知识库辅助模式: {knowledge_status}")
        
        # 检查知识库是否已初始化
        if hasattr(self.assistant, 'knowledge_base'):
            kb_items = self.assistant.knowledge_base.list_items()
            print(f"[DEBUG] 当前知识库条目数量: {len(kb_items)}")
        else:
            print("[WARNING] 知识库组件未初始化") 

    def process_knowledge_results(self, results, message):
        """处理知识库搜索结果，提取相关上下文"""
        if not results or len(results) == 0:
            print("[INFO] 未找到相关知识")
            return None
        
        # 统计结果数量和质量
        high_quality = [r for r in results if r.get('similarity', 0) > 0.7]
        medium_quality = [r for r in results if 0.6 <= r.get('similarity', 0) <= 0.7]
        print(f"[DEBUG] 高质量匹配: {len(high_quality)}, 中等质量匹配: {len(medium_quality)}")
        
        # 提取内容
        knowledge_texts = []
        seen_content = set()  # 避免重复内容
        
        # 优先添加高质量匹配
        for item in sorted(results, key=lambda x: x.get('similarity', 0), reverse=True):
            if isinstance(item, dict) and 'content' in item:
                content = item['content'].strip()
                similarity = item.get('similarity', 0)
                
                # 避免重复内容
                content_hash = hash(content)
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    
                    # 根据相似度决定是否加入知识库
                    if similarity >= 0.6:
                        knowledge_texts.append(f"【相关度: {similarity:.2f}】\n{content}")
                        print(f"[DEBUG] 添加知识片段 (相似度:{similarity:.2f}): {content[:100]}...")
        
        # 合并知识文本
        if knowledge_texts:
            combined_text = "\n\n".join(knowledge_texts)
            print(f"[DEBUG] 合并后的知识长度: {len(combined_text)} 字符")
            return combined_text
        else:
            return None 

    def debug_knowledge_system(self):
        """调试知识库系统状态"""
        print("\n===== 知识库系统诊断 =====")
        
        # 检查知识库组件
        if hasattr(self.assistant, 'knowledge_base'):
            kb = self.assistant.knowledge_base
            print(f"知识库类型: {type(kb).__name__}")
            
            # 检查向量数据库属性
            if hasattr(kb, 'vector_db'):
                vdb = kb.vector_db
                print(f"向量数据库类型: {type(vdb).__name__}")
                
                # 检查向量和集合
                if hasattr(vdb, 'vectors'):
                    print(f"向量数量: {len(vdb.vectors) if vdb.vectors else 0}")
                else:
                    print("缺少vectors属性")
                
                if hasattr(vdb, 'collections'):
                    print(f"集合数量: {len(vdb.collections) if vdb.collections else 0}")
                    # 输出集合内容
                    for name, coll in vdb.collections.items():
                        if isinstance(coll, dict):
                            vectors_count = len(coll.get('vectors', []))
                            texts_count = len(coll.get('texts', []))
                            print(f"  集合 '{name}': {vectors_count} 向量, {texts_count} 文本")
                else:
                    print("缺少collections属性")
                
                # 尝试修复向量数据结构
                if not vdb.vectors and hasattr(vdb, 'collections') and vdb.collections:
                    print("\n尝试从collections修复vectors...")
                    result = self._repair_vectors(vdb)
                    if result:
                        print(f"成功修复，现在有 {len(vdb.vectors)} 个向量")
                    else:
                        print("修复失败")
            else:
                print("知识库缺少向量数据库组件")
        else:
            print("助手不包含知识库组件")
        
        print("===== 诊断完成 =====\n")

    def _repair_vectors(self, vdb):
        """尝试修复向量数据库结构"""
        if not hasattr(vdb, 'collections') or not vdb.collections:
            return False
        
        # 确保vectors属性存在
        if not hasattr(vdb, 'vectors'):
            vdb.vectors = {}
        
        # 从collections重建vectors
        vectors_added = 0
        for coll_name, coll_data in vdb.collections.items():
            if isinstance(coll_data, dict) and 'vectors' in coll_data and 'texts' in coll_data:
                vectors = coll_data['vectors']
                texts = coll_data['texts']
                metadata = coll_data.get('metadata', [{}] * len(vectors))
                
                for i, (vector, text) in enumerate(zip(vectors, texts)):
                    vector_id = f"v_{coll_name}_{i}_{int(time.time())}"
                    vdb.vectors[vector_id] = {
                        'vector': vector,
                        'text': text,
                        'metadata': metadata[i] if i < len(metadata) else {}
                    }
                    vectors_added += 1
        
        return vectors_added > 0 