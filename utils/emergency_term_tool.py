"""术语库应急工具，独立于现有UI架构，直接处理术语数据"""

import os
import sys
import json
from datetime import datetime
import uuid
import time

# 确保模块路径正确
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox,
                              QWidget, QFileDialog, QListWidget, QFormLayout, QProgressDialog, 
                              QDialog)
from PySide6.QtCore import Qt, QTimer, QMetaObject, Q_ARG, Slot

class EmergencyTermTool(QMainWindow):
    """术语库应急工具，简单直接地操作数据文件"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("术语库应急工具")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.resize(800, 600)
        
        # 设置基本路径
        self.term_path = os.path.join('data', 'terms')
        self.vector_path = os.path.join('data', 'term_vectors')
        
        # 确保目录存在
        self.ensure_dir_exists(self.term_path)
        self.ensure_dir_exists(self.vector_path)
        
        # 加载术语数据
        self.terms = self.load_terms()
        
        # 初始化UI
        self.init_ui()
        
        # 显示状态
        self.update_status()
    
    def ensure_dir_exists(self, path):
        """确保目录存在"""
        if not os.path.exists(path):
            os.makedirs(path)
            self.log(f"创建目录: {path}")
    
    def load_terms(self):
        """加载术语数据"""
        terms_file = os.path.join(self.term_path, 'terms.json')
        
        if os.path.exists(terms_file):
            try:
                with open(terms_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.log(f"已加载 {len(data)} 个术语")
                return data
            except Exception as e:
                self.log(f"加载术语数据失败: {e}")
                return {}
        else:
            self.log("术语文件不存在，创建空术语库")
            return {}
    
    def save_terms(self):
        """保存术语数据"""
        terms_file = os.path.join(self.term_path, 'terms.json')
        
        try:
            with open(terms_file, 'w', encoding='utf-8') as f:
                json.dump(self.terms, f, ensure_ascii=False, indent=2)
            self.log(f"已保存 {len(self.terms)} 个术语")
            return True
        except Exception as e:
            self.log(f"保存术语数据失败: {e}")
            QMessageBox.critical(self, "错误", f"保存术语数据失败: {e}")
            return False
    
    def add_term(self, source_term, target_term, source_lang="zh", target_lang="en"):
        """添加术语"""
        if not source_term or not target_term:
            self.log("错误: 术语和定义不能为空")
            return False
        
        try:
            # 生成唯一ID
            term_id = str(uuid.uuid4())
            
            # 创建术语数据
            metadata = {
                'source_lang': source_lang,
                'target_lang': target_lang,
                'type': 'term',
                'added_time': datetime.now().isoformat()
            }
            
            term_data = {
                'source_term': source_term,
                'target_term': target_term,
                'definition': target_term,  # 兼容旧版结构
                'vector_id': None,  # 稍后生成向量
                'metadata': metadata
            }
            
            # 添加到术语库
            self.terms[source_term] = term_data
            
            # 保存术语库
            self.save_terms()
            
            self.log(f"已添加术语: {source_term} -> {target_term}")
            return True
        
        except Exception as e:
            self.log(f"添加术语失败: {e}")
            return False
    
    def import_terms_from_file(self, filename):
        """从文件导入术语"""
        try:
            self.log(f"开始导入文件: {os.path.basename(filename)}")
            
            # 检查文件是否存在
            if not os.path.exists(filename):
                return False, f"文件不存在: {filename}"
            
            # 获取文件扩展名
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            # 检查文件类型并处理
            if ext == '.json':
                # 尝试读取JSON文件
                with open(filename, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        
                        # 识别terminology.json特殊格式
                        if self.is_terminology_format(data):
                            return self.import_terminology_format(data)
                        
                        # 标准术语格式处理
                        return self.import_standard_json(data)
                    except json.JSONDecodeError:
                        return False, "JSON格式错误，无法解析"
            
            elif ext in ['.csv', '.tsv']:
                # CSV/TSV格式
                delimiter = ',' if ext == '.csv' else '\t'
                return self.import_csv_tsv(filename, delimiter)
            
            elif ext == '.txt':
                # 文本格式
                return self.import_txt(filename)
            
            else:
                return False, f"不支持的文件类型: {ext}"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"导入过程中出错: {str(e)}"

    def is_terminology_format(self, data):
        """检查是否是terminology.json特殊格式"""
        # 检查是否为双层嵌套字典结构
        if not isinstance(data, dict):
            return False
        
        # 检查第一级是否只有语言键
        for lang_key, lang_value in data.items():
            if not isinstance(lang_value, dict):
                return False
            
            # 检查第二级是否也是语言键
            for target_lang, terms in lang_value.items():
                if not isinstance(terms, dict):
                    return False
                
                # 第三级应该是术语映射
                for term, definition in terms.items():
                    if not isinstance(term, str) or not isinstance(definition, str):
                        return False
        
        return True

    def import_terminology_format(self, data):
        """导入terminology.json特殊格式"""
        self.log("检测到特殊术语格式，开始导入...")
        
        imported_count = 0
        
        try:
            # 遍历所有语言对
            for source_lang_name, target_langs in data.items():
                # 将语言名称转换为语言代码
                source_lang = self.get_lang_code(source_lang_name)
                
                for target_lang_name, terms in target_langs.items():
                    # 将目标语言名称转换为语言代码
                    target_lang = self.get_lang_code(target_lang_name)
                    
                    self.log(f"导入 {source_lang_name}({source_lang}) -> {target_lang_name}({target_lang}) 术语...")
                    
                    # 导入术语
                    for source_term, target_term in terms.items():
                        if self.add_term(source_term, target_term, source_lang, target_lang):
                            imported_count += 1
                            
                            # 每导入10个术语输出一次日志
                            if imported_count % 10 == 0:
                                self.log(f"已导入 {imported_count} 个术语...")
            
            self.log(f"术语导入完成，共导入 {imported_count} 个术语")
            return True, f"成功导入 {imported_count} 个术语"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"导入特殊格式术语失败: {str(e)}"

    def get_lang_code(self, lang_name):
        """将语言名称转换为语言代码"""
        lang_map = {
            "中文": "zh",
            "英语": "en",
            "英文": "en",
            "日语": "ja",
            "日文": "ja",
            "韩语": "ko",
            "韩文": "ko",
            "法语": "fr",
            "法文": "fr",
            "德语": "de",
            "德文": "de",
            "俄语": "ru",
            "俄文": "ru",
            "西班牙语": "es",
            "西班牙文": "es",
            "葡萄牙语": "pt",
            "葡萄牙文": "pt",
            "意大利语": "it",
            "意大利文": "it"
        }
        
        return lang_map.get(lang_name, lang_name.lower())

    def import_standard_json(self, data):
        """导入标准JSON格式术语"""
        imported_count = 0
        
        try:
            # 检查数据结构
            if isinstance(data, dict):
                # 直接的术语映射
                for source_term, term_data in data.items():
                    if isinstance(term_data, dict):
                        # 复杂术语条目
                        target_term = term_data.get('target_term', term_data.get('definition', ''))
                        source_lang = term_data.get('source_lang', 'zh')
                        target_lang = term_data.get('target_lang', 'en')
                        
                        if self.add_term(source_term, target_term, source_lang, target_lang):
                            imported_count += 1
                    elif isinstance(term_data, str):
                        # 简单术语条目
                        if self.add_term(source_term, term_data):
                            imported_count += 1
            elif isinstance(data, list):
                # 术语列表
                for item in data:
                    if isinstance(item, dict):
                        source_term = item.get('source_term', item.get('term', ''))
                        target_term = item.get('target_term', item.get('definition', ''))
                        source_lang = item.get('source_lang', 'zh')
                        target_lang = item.get('target_lang', 'en')
                        
                        if source_term and target_term:
                            if self.add_term(source_term, target_term, source_lang, target_lang):
                                imported_count += 1
            
            self.log(f"术语导入完成，共导入 {imported_count} 个术语")
            return True, f"成功导入 {imported_count} 个术语"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"导入标准JSON格式术语失败: {str(e)}"
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        # 输出到控制台
        print(log_message)
        
        # 添加到日志文本框
        if hasattr(self, 'log_text'):
            self.log_text.append(log_message)
            self.log_text.ensureCursorVisible()
    
    def init_ui(self):
        """初始化UI"""
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 标题
        title_label = QLabel("术语库应急工具")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 功能区布局
        tool_layout = QHBoxLayout()
        
        # 添加术语按钮
        self.add_btn = QPushButton("添加术语")
        self.add_btn.clicked.connect(self.add_term_ui)
        tool_layout.addWidget(self.add_btn)
        
        # 修改术语按钮
        self.edit_btn = QPushButton("修改术语")
        self.edit_btn.clicked.connect(self.edit_term_ui)
        self.edit_btn.setStyleSheet("background-color: #5cb85c; font-weight: bold;")
        tool_layout.addWidget(self.edit_btn)
        
        # 导入术语按钮
        self.import_btn = QPushButton("导入术语")
        self.import_btn.clicked.connect(self.import_terms_ui)
        tool_layout.addWidget(self.import_btn)
        
        # 导入特定术语库按钮
        self.import_special_btn = QPushButton("导入专业术语库")
        self.import_special_btn.clicked.connect(self.import_terminology)
        self.import_special_btn.setStyleSheet("background-color: #f0ad4e; font-weight: bold;")
        tool_layout.addWidget(self.import_special_btn)
        
        # 生成向量按钮
        self.generate_vectors_btn = QPushButton("生成术语向量")
        self.generate_vectors_btn.clicked.connect(self.generate_vectors_ui)
        self.generate_vectors_btn.setStyleSheet("background-color: #5bc0de; font-weight: bold;")
        tool_layout.addWidget(self.generate_vectors_btn)
        
        # 删除术语按钮
        self.delete_btn = QPushButton("删除术语")
        self.delete_btn.clicked.connect(self.delete_term)
        tool_layout.addWidget(self.delete_btn)
        
        main_layout.addLayout(tool_layout)
        
        # 术语列表和详情区域的分割布局
        split_layout = QHBoxLayout()
        
        # 术语列表区域
        list_layout = QVBoxLayout()
        list_label = QLabel("术语列表:")
        list_layout.addWidget(list_label)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索术语...")
        self.search_input.textChanged.connect(self.filter_terms)
        list_layout.addWidget(self.search_input)
        
        self.term_list = QListWidget()
        self.term_list.currentItemChanged.connect(self.show_term_details)
        list_layout.addWidget(self.term_list)
        
        # 添加列表区域到分割布局
        split_layout.addLayout(list_layout, 1)
        
        # 术语详情区域
        detail_layout = QVBoxLayout()
        self.detail_label = QLabel("术语详情:")
        detail_layout.addWidget(self.detail_label)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        # 添加详情区域到分割布局
        split_layout.addLayout(detail_layout, 2)
        
        # 添加分割布局到主布局
        main_layout.addLayout(split_layout)
        
        # 状态/日志区域
        log_label = QLabel("操作日志:")
        main_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt;")
        main_layout.addWidget(self.log_text)
        
        # 状态栏
        self.status_bar = self.statusBar()
        
        # 显示欢迎信息
        self.log("术语库应急工具已启动")
        self.log(f"术语文件路径: {self.term_path}")
        
        # 刷新术语列表
        self.refresh_term_list()
    
    def update_status(self, message=None):
        """更新状态栏信息"""
        if message:
            # 如果提供了特定消息，显示它
            self.status_bar.showMessage(message, 5000)  # 显示5秒
        else:
            # 否则显示默认的统计信息
            count = len(self.terms)
            self.status_bar.showMessage(f"已加载 {count} 个术语")
    
    def refresh_term_list(self):
        """刷新术语列表"""
        try:
            self.term_list.clear()
            
            # 重新加载术语数据
            self.terms = self.load_terms()
            
            # 添加到列表
            for term in sorted(self.terms.keys()):
                self.term_list.addItem(term)
            
            # 更新状态
            self.update_status()
            
            # 清空详情
            self.detail_text.clear()
            
            self.log(f"刷新术语列表完成，共 {len(self.terms)} 个术语")
        except Exception as e:
            self.log(f"刷新术语列表出错: {e}")
    
    def show_term_details(self, item):
        """显示术语详情"""
        if item is None:
            self.detail_text.clear()
            return
        
        term = item.text()
        if term in self.terms:
            term_data = self.terms[term]
            
            # 将术语数据格式化为文本
            details = f"术语: {term}\n\n"
            
            # 添加基本信息
            target_term = term_data.get('target_term', '') or term_data.get('definition', '')
            details += f"定义: {target_term}\n\n"
            
            # 添加元数据
            metadata = term_data.get('metadata', {})
            if metadata:
                details += "元数据:\n"
                for key, value in metadata.items():
                    details += f"  {key}: {value}\n"
            
            # 显示向量ID
            vector_id = term_data.get('vector_id')
            if vector_id:
                details += f"\n向量ID: {vector_id[:10]}...\n"
            else:
                details += "\n尚未生成向量表示\n"
            
            self.detail_text.setText(details)
        else:
            self.detail_text.setText(f"术语 '{term}' 不存在")
    
    def add_term_ui(self):
        """添加术语的UI界面"""
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("添加术语")
        dialog.resize(400, 300)
        
        # 布局
        layout = QFormLayout(dialog)
        
        # 输入字段
        source_term_input = QLineEdit()
        source_term_input.setPlaceholderText("输入中文术语")
        layout.addRow("中文术语:", source_term_input)
        
        target_term_input = QLineEdit()
        target_term_input.setPlaceholderText("输入英文术语或定义")
        layout.addRow("英文术语:", target_term_input)
        
        source_lang_input = QLineEdit("zh")
        layout.addRow("源语言:", source_lang_input)
        
        target_lang_input = QLineEdit("en")
        layout.addRow("目标语言:", target_lang_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("添加")
        cancel_button = QPushButton("取消")
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addRow("", button_layout)
        
        # 连接信号
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        # 执行对话框
        if dialog.exec():
            # 获取输入
            source_term = source_term_input.text().strip()
            target_term = target_term_input.text().strip()
            source_lang = source_lang_input.text().strip()
            target_lang = target_lang_input.text().strip()
            
            if not source_term or not target_term:
                QMessageBox.warning(self, "输入错误", "术语和定义不能为空")
                return
            
            # 添加术语
            if self.add_term(source_term, target_term, source_lang, target_lang):
                QMessageBox.information(self, "成功", f"成功添加术语: {source_term}")
                self.refresh_term_list()
                
                # 选中新添加的术语
                for i in range(self.term_list.count()):
                    if self.term_list.item(i).text() == source_term:
                        self.term_list.setCurrentRow(i)
                        break
            else:
                QMessageBox.critical(self, "错误", "添加术语失败")
    
    def import_terms_ui(self):
        """导入术语的UI界面"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择术语文件", "", 
            "术语文件 (*.json *.csv *.tsv *.txt)"
        )
        
        if not filename:
            self.log("导入取消")
            return
        
        self.log(f"开始导入文件: {filename}")
        
        # 导入术语
        success, message = self.import_terms_from_file(filename)
        
        if success:
            self.log(f"导入成功: {message}")
            QMessageBox.information(self, "导入成功", message)
            self.refresh_term_list()
        else:
            self.log(f"导入失败: {message}")
            QMessageBox.critical(self, "导入失败", message)
    
    def delete_term(self):
        """删除所选术语"""
        current_item = self.term_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要删除的术语")
            return
        
        term = current_item.text()
        
        # 确认删除
        result = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除术语 '{term}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            try:
                # 删除术语
                if term in self.terms:
                    del self.terms[term]
                    
                    # 保存
                    self.save_terms()
                    
                    self.log(f"已删除术语: {term}")
                    self.refresh_term_list()
                else:
                    self.log(f"术语不存在: {term}")
            except Exception as e:
                self.log(f"删除术语失败: {e}")
                QMessageBox.critical(self, "错误", f"删除术语失败: {e}")

    @Slot(str, str)
    def show_success_message(self, title, message):
        """显示成功消息"""
        QMessageBox.information(self, title, message)

    @Slot(str, str)
    def show_error_message(self, title, message):
        """显示错误消息"""
        QMessageBox.critical(self, title, message)

    def generate_vectors(self):
        """为术语生成向量表示"""
        self.log("\n===== 开始生成术语向量 =====")
        
        # 检查是否有可用的向量模型
        try:
            # 使用主应用程序的向量模型
            from utils.vector_utils import load_vector_model, get_embedding
            
            # 加载向量模型
            self.log("尝试加载向量模型...")
            
            # 尝试几个可能的模型路径位置
            model_paths = [
                os.path.join('BAAI', 'bge-m3'),
                os.path.join('d:', 'AI_project', 'vllm_模型应用', 'BAAI', 'bge-m3'),
                os.path.join('d:', 'AI_project', 'vllm_模型应用', 'bge-base-zh-v1.5')
            ]
            
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    self.log(f"找到向量模型: {path}")
                    break
            
            if not model_path:
                self.log("找不到向量模型，将保存术语但不生成向量")
                return False
            
            self.log(f"尝试加载向量模型: {model_path}")
            model = load_vector_model(model_path)
            
            if not model:
                self.log("向量模型加载失败，术语将不会有向量表示")
                return False
            
            self.log("向量模型加载成功，开始生成向量...")
            
            # 为每个术语生成向量
            vectorized_count = 0
            vectors_data = {}
            
            for term, term_data in self.terms.items():
                try:
                    # 生成向量
                    vector = get_embedding(model, term)
                    
                    if vector is not None:
                        # 生成向量ID
                        vector_id = str(uuid.uuid4())
                        
                        # 保存向量
                        vectors_data[vector_id] = {
                            'content': term,
                            'vector': vector.tolist(),
                            'metadata': term_data.get('metadata', {})
                        }
                        
                        # 更新术语数据
                        term_data['vector_id'] = vector_id
                        self.terms[term] = term_data
                        
                        vectorized_count += 1
                        
                        # 每处理10个术语输出一次日志
                        if vectorized_count % 10 == 0:
                            self.log(f"已为 {vectorized_count} 个术语生成向量...")
                
                except Exception as e:
                    self.log(f"为术语 '{term}' 生成向量时出错: {e}")
            
            # 保存向量数据
            self.log("保存向量数据...")
            vector_file = os.path.join(self.vector_path, 'vectors.json')
            
            with open(vector_file, 'w', encoding='utf-8') as f:
                json.dump(vectors_data, f, ensure_ascii=False, indent=2)
            
            # 保存更新后的术语数据
            self.save_terms()
            
            self.log(f"成功为 {vectorized_count} 个术语生成向量表示")
            return True
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"生成向量表示失败: {e}")
            return False

    def import_terminology(self):
        """导入terminology.json术语库"""
        try:
            # 设置默认路径
            default_paths = [
                os.path.join('Terms', 'terminology.json'),
                os.path.join('d:', 'AI_project', 'AI翻译_olama', 'Terms', 'terminology.json')
            ]
            
            # 检查默认路径是否存在
            filename = None
            for path in default_paths:
                if os.path.exists(path):
                    filename = path
                    self.log(f"找到默认术语库文件: {path}")
                    break
            
            # 如果默认路径不存在，让用户选择
            if not filename:
                filename, _ = QFileDialog.getOpenFileName(
                    self, "选择术语库文件", "", 
                    "术语库文件 (terminology.json)"
                )
            
            if not filename:
                self.log("取消导入")
                return
            
            # 确认导入
            confirm = QMessageBox.question(
                self, "确认导入", 
                f"确定要导入术语库文件: {filename}?\n这可能会覆盖现有的术语。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm != QMessageBox.Yes:
                self.log("取消导入")
                return
            
            self.log(f"开始导入术语库文件: {filename}")
            
            # 导入术语
            success, message = self.import_terms_from_file(filename)
            
            if success:
                self.log(f"导入成功: {message}")
                QMessageBox.information(self, "导入成功", message)
                
                # 刷新术语列表
                self.refresh_term_list()
                
                # 询问是否生成向量
                ask_generate = QMessageBox.question(
                    self, "生成向量", 
                    "是否要为导入的术语生成向量表示?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if ask_generate == QMessageBox.Yes:
                    self.generate_vectors_ui()
            else:
                self.log(f"导入失败: {message}")
                QMessageBox.critical(self, "导入失败", message)
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"导入术语库文件失败: {e}")
            QMessageBox.critical(self, "错误", f"导入术语库文件失败: {str(e)}")

    def generate_vectors_ui(self):
        """生成向量表示UI"""
        try:
            if not self.terms:
                QMessageBox.warning(self, "警告", "术语库为空，无需生成向量")
                return
            
            # 确认生成
            confirm = QMessageBox.question(
                self, "确认生成向量", 
                f"确定要为 {len(self.terms)} 个术语生成向量表示?\n这可能需要一些时间。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm != QMessageBox.Yes:
                self.log("取消生成向量")
                return
            
            self.log("开始生成术语向量...")
            
            # 显示进度对话框
            progress = QProgressDialog("正在生成术语向量...", "取消", 0, 100, self)
            progress.setWindowTitle("处理中")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(10)
            progress.show()
            
            # 后台生成向量
            import threading
            
            def run_task():
                result = self.generate_vectors()
                QMetaObject.invokeMethod(
                    progress, "close", 
                    Qt.QueuedConnection
                )
                if result:
                    QMetaObject.invokeMethod(
                        self, "show_success_message", 
                        Qt.QueuedConnection,
                        Q_ARG(str, "向量生成完成"),
                        Q_ARG(str, f"成功为术语生成向量表示")
                    )
                else:
                    QMetaObject.invokeMethod(
                        self, "show_error_message", 
                        Qt.QueuedConnection,
                        Q_ARG(str, "向量生成失败"),
                        Q_ARG(str, f"无法为术语生成向量表示，请查看日志")
                    )
            
            thread = threading.Thread(target=run_task)
            thread.daemon = True
            thread.start()
            
            # 更新进度
            def update_progress():
                if progress.wasCanceled():
                    return
                
                current = progress.value()
                if current < 90:
                    progress.setValue(current + 10)
                    QTimer.singleShot(500, update_progress)
                else:
                    progress.setValue(100)
            
            QTimer.singleShot(500, update_progress)
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"生成向量操作失败: {e}")
            QMessageBox.critical(self, "错误", f"生成向量操作失败: {str(e)}")

    def edit_term_ui(self):
        """修改术语的UI界面"""
        # 获取当前选中的术语
        selected = self.term_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要修改的术语")
            return
        
        # 获取当前选中的术语名称
        term_name = selected.text()
        
        # 获取术语数据
        if term_name not in self.terms:
            QMessageBox.critical(self, "错误", f"找不到术语: {term_name}")
            return
        
        term_data = self.terms[term_name]
        
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("修改术语")
        dialog.resize(500, 400)
        dialog.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        # 创建表单布局
        layout = QFormLayout(dialog)
        
        # 源术语输入框
        source_term_input = QLineEdit(term_name)
        layout.addRow("源术语:", source_term_input)
        
        # 获取目标术语和定义
        target_term = term_data.get('target_term', term_data.get('definition', ''))
        
        # 目标术语输入框
        target_term_input = QLineEdit(target_term)
        layout.addRow("目标术语/定义:", target_term_input)
        
        # 获取源语言和目标语言
        metadata = term_data.get('metadata', {})
        source_lang = metadata.get('source_lang', 'zh')
        target_lang = metadata.get('target_lang', 'en')
        
        # 源语言输入框
        source_lang_input = QLineEdit(source_lang)
        layout.addRow("源语言:", source_lang_input)
        
        # 目标语言输入框
        target_lang_input = QLineEdit(target_lang)
        layout.addRow("目标语言:", target_lang_input)
        
        # 重新生成向量复选框
        regenerate_vector = False
        regenerate_check = QPushButton("重新生成向量")
        regenerate_check.setCheckable(True)
        regenerate_check.setChecked(False)
        regenerate_check.toggled.connect(lambda checked: setattr(dialog, 'regenerate_vector', checked))
        layout.addRow("向量管理:", regenerate_check)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow("", button_layout)
        
        # 设置按钮事件
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            # 获取新值
            new_source_term = source_term_input.text().strip()
            new_target_term = target_term_input.text().strip()
            new_source_lang = source_lang_input.text().strip()
            new_target_lang = target_lang_input.text().strip()
            
            # 验证输入
            if not new_source_term or not new_target_term:
                QMessageBox.critical(self, "错误", "源术语和目标术语不能为空")
                return
            
            # 检查是否修改了源术语名称
            if new_source_term != term_name:
                # 如果修改了源术语，需要创建新条目并删除旧条目
                # 保存旧向量ID
                old_vector_id = term_data.get('vector_id')
                
                # 从术语库中删除旧术语
                del self.terms[term_name]
                
                # 创建新的术语数据
                new_metadata = metadata.copy()
                new_metadata.update({
                    'source_lang': new_source_lang,
                    'target_lang': new_target_lang,
                    'updated_time': datetime.now().isoformat()
                })
                
                new_term_data = {
                    'source_term': new_source_term,
                    'target_term': new_target_term,
                    'definition': new_target_term,  # 兼容旧结构
                    'vector_id': old_vector_id,  # 保留原向量ID
                    'metadata': new_metadata
                }
                
                # 添加新术语
                self.terms[new_source_term] = new_term_data
                
                # 如果需要重新生成向量
                if getattr(dialog, 'regenerate_vector', False) or old_vector_id is None:
                    self.generate_vector_for_term(new_source_term)
            else:
                # 如果只修改了其他字段，直接更新术语数据
                # 更新元数据
                metadata.update({
                    'source_lang': new_source_lang,
                    'target_lang': new_target_lang,
                    'updated_time': datetime.now().isoformat()
                })
                
                # 更新术语数据
                term_data.update({
                    'target_term': new_target_term,
                    'definition': new_target_term,  # 兼容旧结构
                    'metadata': metadata
                })
                
                # 更新术语库
                self.terms[term_name] = term_data
                
                # 如果需要重新生成向量
                if getattr(dialog, 'regenerate_vector', False):
                    self.generate_vector_for_term(term_name)
            
            # 保存术语库
            self.save_terms()
            
            # 刷新术语列表
            self.refresh_term_list()
            
            # 日志
            self.log(f"术语 '{term_name}' 已修改")
            
            # 更新状态
            self.update_status(f"修改术语 '{term_name}' 成功")
    
    def generate_vector_for_term(self, term):
        """为单个术语生成向量表示"""
        self.log(f"开始为术语 '{term}' 生成向量...")
        
        try:
            # 确保术语存在
            if term not in self.terms:
                self.log(f"术语 '{term}' 不存在")
                return False
            
            # 使用主应用程序的向量模型
            from utils.vector_utils import load_vector_model, get_embedding
            
            # 加载向量模型
            self.log("尝试加载向量模型...")
            
            # 尝试几个可能的模型路径位置
            model_paths = [
                os.path.join('BAAI', 'bge-m3'),
                os.path.join('d:', 'AI_project', 'vllm_模型应用', 'BAAI', 'bge-m3'),
                os.path.join('d:', 'AI_project', 'vllm_模型应用', 'bge-base-zh-v1.5')
            ]
            
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    self.log(f"找到向量模型: {path}")
                    break
            
            if not model_path:
                self.log("找不到向量模型，无法生成向量")
                return False
            
            model = load_vector_model(model_path)
            
            if not model:
                self.log("向量模型加载失败，无法生成向量")
                return False
            
            # 获取术语数据
            term_data = self.terms[term]
            
            # 生成向量
            vector = get_embedding(model, term)
            
            if vector is not None:
                # 加载当前向量数据
                vector_file = os.path.join(self.vector_path, 'vectors.json')
                vectors_data = {}
                
                if os.path.exists(vector_file):
                    try:
                        with open(vector_file, 'r', encoding='utf-8') as f:
                            vectors_data = json.load(f)
                    except:
                        self.log("无法加载现有向量数据，将创建新文件")
                
                # 移除旧向量ID
                old_vector_id = term_data.get('vector_id')
                if old_vector_id and old_vector_id in vectors_data:
                    del vectors_data[old_vector_id]
                    self.log(f"已移除旧向量ID: {old_vector_id}")
                
                # 生成新的向量ID
                vector_id = str(uuid.uuid4())
                
                # 保存向量
                vectors_data[vector_id] = {
                    'content': term,
                    'vector': vector.tolist(),
                    'metadata': term_data.get('metadata', {})
                }
                
                # 更新术语数据
                term_data['vector_id'] = vector_id
                self.terms[term] = term_data
                
                # 保存向量数据
                with open(vector_file, 'w', encoding='utf-8') as f:
                    json.dump(vectors_data, f, ensure_ascii=False, indent=2)
                
                # 保存术语数据
                self.save_terms()
                
                self.log(f"已为术语 '{term}' 生成向量表示")
                return True
            else:
                self.log(f"为术语 '{term}' 生成向量失败")
                return False
        
        except Exception as e:
            self.log(f"生成术语向量时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def filter_terms(self, text):
        """按搜索文本过滤术语列表"""
        if not text:
            # 如果搜索框为空，显示所有术语
            self.refresh_term_list()
            return
        
        # 清空列表
        self.term_list.clear()
        
        # 查找匹配的术语
        for term in self.terms:
            if text.lower() in term.lower():
                self.term_list.addItem(term)
        
        # 更新状态
        count = self.term_list.count()
        self.update_status(f"找到 {count} 个匹配术语")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            # 保存数据
            self.save_terms()
            
            # 记录日志
            self.log("术语库工具已关闭")
            
            # 清理全局引用
            import utils.term_tools as term_tools
            if hasattr(term_tools, 'term_tool_window'):
                term_tools.term_tool_window = None
            
            # 接受关闭事件
            event.accept()
        except Exception as e:
            print(f"[ERROR] 关闭术语工具时出错: {e}")
            event.accept()

def run():
    """运行应急工具"""
    try:
        # 检查是否已存在应用程序实例
        app = QApplication.instance()
        new_app_created = False
        
        if app is None:
            app = QApplication(sys.argv)
            new_app_created = True
        
        # 创建并显示工具窗口
        window = EmergencyTermTool()
        window.show()
        
        # 只有在创建了新的应用程序实例时才执行事件循环
        if new_app_created:
            return app.exec()
        else:
            # 如果已有事件循环，只需返回成功
            return 0
    except Exception as e:
        print(f"[ERROR] 启动术语工具失败: {e}")
        import traceback
        traceback.print_exc()
        return -1

if __name__ == "__main__":
    run() 