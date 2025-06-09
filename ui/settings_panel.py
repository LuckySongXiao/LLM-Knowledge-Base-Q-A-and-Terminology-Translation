from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QLineEdit, QGroupBox, QFormLayout, QCheckBox, QSlider,
                             QFileDialog, QTextEdit, QTabWidget, QProgressBar, QListWidget,
                             QMessageBox, QComboBox, QListWidgetItem, QInputDialog, QProgressDialog)
from PySide6.QtCore import Qt, Signal
from core.model_manager import ModelManager
import os
import threading

class SettingsPanel(QWidget):
    """设置面板"""
    
    # 添加新的信号
    progress_updated = Signal(QProgressDialog, int)
    download_complete = Signal(str, bool, str)
    path_updated = Signal(QLineEdit, str)
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.i18n = assistant.i18n
        self.settings = assistant.settings
        
        self.init_ui()
        
        # 连接信号
        self.progress_updated.connect(self._update_progress)
        self.download_complete.connect(self._show_download_result)
        self.path_updated.connect(self._update_path)
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建设置选项卡
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # 模型设置选项卡
        model_tab = QWidget()
        tabs.addTab(model_tab, self.i18n.translate("model_settings"))
        
        model_layout = QFormLayout()
        
        # AI模型路径
        model_container = self.init_model_settings()
        model_layout.addRow("", model_container)
        
        # 向量模型路径
        vector_path_layout = QHBoxLayout()
        self.vector_model_path = QLineEdit(self.settings.get('vector_model_path', ''))
        vector_path_layout.addWidget(self.vector_model_path)
        
        browse_vector = QPushButton(self.i18n.translate("browse"))
        browse_vector.clicked.connect(lambda: self.browse_file(self.vector_model_path))
        vector_path_layout.addWidget(browse_vector)
        
        # 添加向量模型下载按钮
        vector_download = QPushButton(self.i18n.translate("download"))
        vector_download.clicked.connect(self.download_embedding_model)
        vector_path_layout.addWidget(vector_download)
        
        model_layout.addRow(self.i18n.translate("vector_model_path"), vector_path_layout)
        
        # 添加语音模型路径（如果需要）
        voice_path_layout = QHBoxLayout()
        self.voice_model_path = QLineEdit(self.settings.get('voice_model_path', ''))
        voice_path_layout.addWidget(self.voice_model_path)
        
        browse_voice = QPushButton(self.i18n.translate("browse"))
        browse_voice.clicked.connect(lambda: self.browse_file(self.voice_model_path))
        voice_path_layout.addWidget(browse_voice)
        
        model_layout.addRow(self.i18n.translate("voice_model_path"), voice_path_layout)
        
        # 超参数设置
        hyperparams_group = QGroupBox(self.i18n.translate("hyperparameters"))
        hyperparams_layout = QFormLayout()
        
        self.temperature = QSlider(Qt.Horizontal)
        self.temperature.setRange(0, 100)
        self.temperature.setValue(int(self.settings.get('hyperparams', {}).get('temperature', 0.7) * 100))
        hyperparams_layout.addRow(self.i18n.translate("temperature"), self.temperature)
        
        self.max_length = QLineEdit(str(self.settings.get('hyperparams', {}).get('max_length', 2048)))
        hyperparams_layout.addRow(self.i18n.translate("max_length"), self.max_length)
        
        hyperparams_group.setLayout(hyperparams_layout)
        model_layout.addRow("", hyperparams_group)
        
        # 添加模型量化设置组
        quant_group = QGroupBox("模型量化设置")
        quant_layout = QFormLayout()
        
        # 启用自动量化的复选框
        self.enable_auto_quant = QCheckBox("启用自动量化")
        self.enable_auto_quant.setChecked(self.settings.get("enable_auto_quantization", True))
        quant_layout.addRow("", self.enable_auto_quant)
        
        # 量化级别选择
        self.quant_level = QComboBox()
        self.quant_level.addItem("自动选择", "AUTO")
        self.quant_level.addItem("不量化 (原始精度)", "NONE")
        self.quant_level.addItem("FP16 (半精度浮点)", "FP16")
        self.quant_level.addItem("INT8 (8位整数)", "INT8")
        self.quant_level.addItem("INT4 (4位整数)", "INT4")
        
        # 设置当前选择
        current_level = self.settings.get("quantization_level", "AUTO")
        index = self.quant_level.findData(current_level)
        if index >= 0:
            self.quant_level.setCurrentIndex(index)
        else:
            # 如果找不到对应的选项，默认使用自动选择
            self.quant_level.setCurrentIndex(0)
        
        quant_layout.addRow("量化级别:", self.quant_level)
        
        # 内存优化选项
        self.low_cpu_mem = QCheckBox("低CPU内存使用")
        self.low_cpu_mem.setChecked(self.settings.get("memory_optimization", {}).get("low_cpu_mem_usage", True))
        quant_layout.addRow("", self.low_cpu_mem)
        
        self.use_offload = QCheckBox("在显存不足时卸载到CPU")
        self.use_offload.setChecked(self.settings.get("memory_optimization", {}).get("use_offload", True))
        quant_layout.addRow("", self.use_offload)
        
        # 状态显示
        status_label = QLabel("注意: 模型量化设置将在下次加载模型时生效")
        quant_layout.addRow("", status_label)
        
        quant_group.setLayout(quant_layout)
        model_layout.addRow("", quant_group)
        
        model_tab.setLayout(model_layout)
        
        # 人设设置选项卡
        persona_tab = QWidget()
        tabs.addTab(persona_tab, self.i18n.translate("persona"))
        
        persona_layout = QVBoxLayout()
        persona_layout.addWidget(QLabel(self.i18n.translate("ai_persona")))
        
        self.persona_text = QTextEdit()
        self.persona_text.setText(self.settings.get('persona', ''))
        persona_layout.addWidget(self.persona_text)
        
        persona_tab.setLayout(persona_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        save_button = QPushButton(self.i18n.translate("save_settings"))
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        
        test_button = QPushButton(self.i18n.translate("test_models"))
        test_button.clicked.connect(self.test_models)
        button_layout.addWidget(test_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def init_model_settings(self):
        """初始化模型设置"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 模型路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel(self.i18n.translate("llm_model_path")))
        
        self.model_path_edit = QLineEdit(self.settings.get('model_path', ''))
        path_layout.addWidget(self.model_path_edit)
        
        browse_button = QPushButton(self.i18n.translate("browse"))
        browse_button.clicked.connect(lambda: self.browse_file(self.model_path_edit))
        path_layout.addWidget(browse_button)
        
        # 添加下载按钮并连接到下载函数
        download_button = QPushButton(self.i18n.translate("download"))
        download_button.clicked.connect(self.download_llm_model)
        path_layout.addWidget(download_button)
        
        layout.addLayout(path_layout)
        
        # 向量模型下载按钮
        vector_download = QPushButton(self.i18n.translate("download"))
        vector_download.clicked.connect(self.download_embedding_model)
        
        # TTS模型下载按钮
        tts_download = QPushButton(self.i18n.translate("download"))
        tts_download.clicked.connect(self.download_tts_model)
        
        # 在初始化声音模型路径和向量模型路径的布局时，添加下载按钮
        # 这段代码在init_ui方法中
        
        return container

    def select_model_path(self):
        """选择模型路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            self.i18n.translate("select_model_path"),
            self.model_path_edit.text()
        )
        
        if path:
            self.model_path_edit.setText(path)
            # 设置路径并检测模型
            self.model_manager.set_model_path(path)
            # 刷新模型列表
            self.refresh_models_list()
            # 刷新推荐模型
            self.load_recommended_models()

    def refresh_models_list(self):
        """刷新模型列表"""
        self.models_list.clear()
        
        # 先显示对话模型
        models = self.model_manager.detect_models(
            self.model_path_edit.text(), 
            self.model_manager.MODEL_TYPE_LLM
        )
        
        if models:
            self.models_list.addItem("--- 对话模型 ---")
            for model in models:
                item = QListWidgetItem(f"{model['name']} ({model['size']:.1f} GB)")
                item.setData(Qt.UserRole, model)
                self.models_list.addItem(item)
        
        # 显示向量模型
        vector_path = self.assistant.settings.get('vector_model_path', '')
        vector_models = self.model_manager.detect_models(
            vector_path,
            self.model_manager.MODEL_TYPE_EMBEDDING
        )
        
        if vector_models:
            self.models_list.addItem("--- 向量模型 ---")
            for model in vector_models:
                item = QListWidgetItem(f"{model['name']} ({model['size']:.1f} GB)")
                item.setData(Qt.UserRole, model)
                self.models_list.addItem(item)
        
        # 显示语音模型
        tts_path = self.assistant.settings.get('voice_model_path', '')
        tts_models = self.model_manager.detect_models(
            tts_path,
            self.model_manager.MODEL_TYPE_TTS
        )
        
        if tts_models:
            self.models_list.addItem("--- 语音模型 ---")
            for model in tts_models:
                item = QListWidgetItem(f"{model['name']} ({model['size']:.1f} GB)")
                item.setData(Qt.UserRole, model)
                self.models_list.addItem(item)

    def load_recommended_models(self):
        """加载推荐模型"""
        self.recommended_combo.clear()
        recommended = self.model_manager.get_recommended_models()
        
        for model in recommended:
            self.recommended_combo.addItem(
                f"{model['name']} ({model.get('required_gpu_memory', 0):.1f} GB GPU / {model.get('required_memory', 0):.1f} GB RAM)",
                model['id']
            )

    def download_selected_model(self):
        """下载选中的模型"""
        if self.recommended_combo.count() == 0:
            return
        
        model_id = self.recommended_combo.currentData()
        
        # 开始下载
        success = self.model_manager.download_model(model_id)
        if success:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.download_button.setEnabled(False)

    def update_download_progress(self, model_id, progress):
        """更新下载进度"""
        self.progress_bar.setValue(int(progress * 100))

    def on_download_complete(self, model_id):
        """下载完成处理"""
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        self.refresh_models_list()
        
        QMessageBox.information(
            self,
            self.i18n.translate("download_complete"),
            self.i18n.translate("model_download_success").format(model_id=model_id)
        )

    def on_download_error(self, model_id, error):
        """下载错误处理"""
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        
        QMessageBox.critical(
            self,
            self.i18n.translate("download_error"),
            self.i18n.translate("model_download_error").format(model_id=model_id, error=error)
        )
    
    def browse_file(self, line_edit):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, self.i18n.translate("browse"), "")
        if file_path:
            line_edit.setText(file_path)
    
    def save_settings(self):
        """保存设置"""
        # 保存模型路径
        self.settings.set('model_path', self.model_path_edit.text())
        self.settings.set('voice_model_path', self.voice_model_path.text())
        self.settings.set('vector_model_path', self.vector_model_path.text())
        
        # 保存超参数
        hyperparams = {
            'temperature': self.temperature.value() / 100,
            'max_length': int(self.max_length.text()),
        }
        self.settings.set('hyperparams', hyperparams)
        
        # 保存人设
        self.settings.set('persona', self.persona_text.toPlainText())
        
        # 保存模型量化设置
        self.settings.set('enable_auto_quantization', self.enable_auto_quant.isChecked())
        self.settings.set('quantization_level', self.quant_level.currentData())
        
        # 保存内存优化设置
        memory_optimization = {
            'low_cpu_mem_usage': self.low_cpu_mem.isChecked(),
            'use_offload': self.use_offload.isChecked(),
            'offload_folder': 'offload_folder'  # 使用默认值
        }
        self.settings.set('memory_optimization', memory_optimization)
        
        # 更新AI引擎
        self.assistant.ai_engine.update_settings(self.settings.get_all())
        
        # 提示保存成功
        self.assistant.main_window.statusBar().showMessage(
            self.i18n.translate("settings_saved"), 3000
        )
    
    def test_models(self):
        """测试模型加载"""
        # 实现模型测试功能
        pass 

    def download_llm_model(self):
        """下载LLM模型"""
        models = [
            {"name": "Qwen2-0.5B", "id": "Qwen/Qwen2-0.5B-Instruct"},
            {"name": "Qwen2-1.5B", "id": "Qwen/Qwen2-1.5B-Instruct"},
            {"name": "Qwen2-7B", "id": "Qwen/Qwen2-7B-Instruct"},
            {"name": "Qwen1.5-7B", "id": "Qwen/Qwen1.5-7B-Chat"}
        ]
        
        # 显示模型选择对话框
        model_name, ok = QInputDialog.getItem(
            self, 
            self.i18n.translate("select_model"),
            self.i18n.translate("select_model_to_download"),
            [m["name"] for m in models],
            0, False
        )
        
        if not ok:
            return
        
        # 获取选中的模型信息
        model_info = next((m for m in models if m["name"] == model_name), None)
        if not model_info:
            return
        
        # 设置下载路径
        download_dir = os.path.join('QWEN', model_name.replace('/', '-'))
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # 创建进度对话框
        progress_dialog = QProgressDialog(
            self.i18n.translate("downloading_model").format(model_name),
            self.i18n.translate("cancel"),
            0, 100,
            self
        )
        progress_dialog.setWindowTitle(self.i18n.translate("download"))
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # 启动下载线程
        download_thread = threading.Thread(
            target=self._download_model_thread,
            args=(model_info["id"], download_dir, progress_dialog, self.model_path_edit, "llm")
        )
        download_thread.daemon = True
        download_thread.start()

    def download_embedding_model(self):
        """下载嵌入模型"""
        models = [
            {"name": "BGE-M3", "id": "BAAI/bge-m3"},
            {"name": "BGE-Small", "id": "BAAI/bge-small-en-v1.5"},
            {"name": "Text2Vec", "id": "GanymedeNil/text2vec-large-chinese"}
        ]
        
        # 显示模型选择对话框
        model_name, ok = QInputDialog.getItem(
            self, 
            self.i18n.translate("select_model"),
            self.i18n.translate("select_model_to_download"),
            [m["name"] for m in models],
            0, False
        )
        
        if not ok:
            return
        
        # 获取选中的模型信息
        model_info = next((m for m in models if m["name"] == model_name), None)
        if not model_info:
            return
        
        # 设置下载路径
        download_dir = os.path.join('BAAI', model_name.replace('/', '-'))
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # 创建进度对话框
        progress_dialog = QProgressDialog(
            self.i18n.translate("downloading_model").format(model_name),
            self.i18n.translate("cancel"),
            0, 100,
            self
        )
        progress_dialog.setWindowTitle(self.i18n.translate("download"))
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # 启动下载线程
        download_thread = threading.Thread(
            target=self._download_model_thread,
            args=(model_info["id"], download_dir, progress_dialog, self.vector_model_path, "embedding")
        )
        download_thread.daemon = True
        download_thread.start()

    def download_tts_model(self):
        """下载TTS模型"""
        models = [
            {"name": "Spark-TTS-0.5B", "id": "SparkAudio/Spark-TTS-0.5B"},
            {"name": "Speech-T5", "id": "microsoft/speecht5_tts"}
        ]
        
        # 显示模型选择对话框
        model_name, ok = QInputDialog.getItem(
            self, 
            self.i18n.translate("select_model"),
            self.i18n.translate("select_model_to_download"),
            [m["name"] for m in models],
            0, False
        )
        
        if not ok:
            return
        
        # 获取选中的模型信息
        model_info = next((m for m in models if m["name"] == model_name), None)
        if not model_info:
            return
        
        # 设置下载路径
        download_dir = os.path.join('TTS', 'models', model_name.replace('/', '-'))
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # 创建进度对话框
        progress_dialog = QProgressDialog(
            self.i18n.translate("downloading_model").format(model_name),
            self.i18n.translate("cancel"),
            0, 100,
            self
        )
        progress_dialog.setWindowTitle(self.i18n.translate("download"))
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # 启动下载线程
        download_thread = threading.Thread(
            target=self._download_model_thread,
            args=(model_info["id"], download_dir, progress_dialog, self.voice_model_path, "tts")
        )
        download_thread.daemon = True
        download_thread.start()

    def _download_model_thread(self, model_id, download_dir, progress_dialog, path_widget, model_type):
        """在线程中下载模型"""
        try:
            from modelscope.hub.snapshot_download import snapshot_download
            import os, time
            
            # 开始下载前显示进度为10%
            self.progress_updated.emit(progress_dialog, 0.1)
            
            # 由于snapshot_download不支持progress_callback，我们改为不传递该参数
            print(f"开始下载模型: {model_id} 到 {download_dir}")
            
            # 启动下载（无进度回调）
            model_path = snapshot_download(
                model_id, 
                cache_dir=download_dir
            )
            
            # 下载完成，显示100%进度
            self.progress_updated.emit(progress_dialog, 1.0)
            
            # 更新路径
            self.path_updated.emit(path_widget, model_path)
            
            # 通知下载完成
            print(f"模型 {model_id} 下载完成")
            self.download_complete.emit(model_id, True, "")
            
        except Exception as e:
            # 下载失败
            print(f"下载模型失败: {e}")
            self.download_complete.emit(model_id, False, str(e))
            import traceback
            traceback.print_exc()

    def _update_progress(self, dialog, progress):
        """更新进度对话框"""
        if dialog and dialog.isVisible():
            dialog.setValue(int(progress * 100))
    
    def _show_download_result(self, model_id, success, error_msg):
        """显示下载结果"""
        if success:
            QMessageBox.information(
                self,
                self.i18n.translate("download_complete"),
                self.i18n.translate("model_download_success").format(model_id=model_id)
            )
        else:
            QMessageBox.warning(
                self,
                self.i18n.translate("download_error"),
                self.i18n.translate("model_download_error").format(model_id=model_id, error=error_msg)
            )
    
    def _update_path(self, widget, path):
        """更新路径文本框"""
        if widget:
            widget.setText(path) 