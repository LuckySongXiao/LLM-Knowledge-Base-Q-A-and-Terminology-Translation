from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QListWidget, QLabel, QComboBox, QFileDialog,
                            QProgressBar, QMessageBox, QInputDialog, QGroupBox,
                            QFormLayout, QLineEdit, QSpinBox, QDialog, QTextEdit,
                            QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QMetaObject, Q_ARG, QTimer, Slot
from PySide6.QtMultimedia import QAudioInput, QMediaRecorder, QMediaCaptureSession, QMediaDevices
import os
import threading
import random
import time
import json
import importlib

try:
    import pyaudio
    import wave
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("PyAudio未安装，将使用PySide6的录音功能")

class VoicePanel(QWidget):
    """语音设置面板"""
    
    # 定义所需的信号
    voiceChanged = Signal(str)  # 语音变更信号
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.i18n = assistant.i18n
        self.tts_engine = assistant.tts_engine if hasattr(assistant, 'tts_engine') else None
        
        self.init_ui()
        self.refresh_voice_list()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 语音选择区域
        voice_group = QGroupBox(self.i18n.translate("voice_selection"))
        voice_layout = QVBoxLayout()
        
        # 语音下拉列表
        voice_selector_layout = QHBoxLayout()
        voice_selector_layout.addWidget(QLabel(self.i18n.translate("current_voice")))
        
        self.voice_selector = QComboBox()
        self.voice_selector.currentTextChanged.connect(self.change_voice)
        voice_selector_layout.addWidget(self.voice_selector)
        
        # 测试按钮
        self.test_button = QPushButton(self.i18n.translate("test_voice"))
        self.test_button.clicked.connect(self.test_voice)
        voice_selector_layout.addWidget(self.test_button)
        
        voice_layout.addLayout(voice_selector_layout)
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # 自定义语音训练区域
        training_group = QGroupBox(self.i18n.translate("voice_training"))
        training_layout = QVBoxLayout()
        
        # 训练说明
        training_desc = QLabel(self.i18n.translate("voice_training_desc"))
        training_desc.setWordWrap(True)
        training_layout.addWidget(training_desc)
        
        # 显示模型信息
        model_info = QLabel("使用模型: Spark-TTS-0.5B")
        model_info.setStyleSheet("color: #666; font-style: italic;")
        training_layout.addWidget(model_info)
        
        # 训练参数设置
        params_layout = QFormLayout()
        
        # 添加语音名称输入
        self.voice_name_input = QLineEdit()
        self.voice_name_input.setPlaceholderText("请输入自定义语音名称")
        params_layout.addRow("语音名称:", self.voice_name_input)
        
        # 添加训练轮数设置
        self.epochs_input = QSpinBox()
        self.epochs_input.setRange(20, 500)
        self.epochs_input.setValue(100)
        self.epochs_input.setSingleStep(10)
        params_layout.addRow("训练轮数:", self.epochs_input)
        
        # 添加学习率设置
        self.learning_rate_combo = QComboBox()
        self.learning_rate_combo.addItems(["0.001", "0.0005", "0.0001", "0.00005"])
        self.learning_rate_combo.setCurrentIndex(2)  # 默认选择0.0001
        params_layout.addRow("学习率:", self.learning_rate_combo)
        
        training_layout.addLayout(params_layout)
        
        # 添加录音文件列表和管理区域
        recordings_group = QGroupBox("录音文件")
        recordings_layout = QVBoxLayout()
        
        # 录音文件列表
        self.recordings_list = QListWidget()
        self.recordings_list.setSelectionMode(QListWidget.ExtendedSelection)
        recordings_layout.addWidget(self.recordings_list)
        
        # 录音文件操作按钮
        recordings_buttons = QHBoxLayout()
        
        # 录制按钮
        self.record_button = QPushButton("录制音频")
        self.record_button.clicked.connect(self.record_audio)
        recordings_buttons.addWidget(self.record_button)
        
        # 导入按钮
        self.import_button = QPushButton("导入音频")
        self.import_button.clicked.connect(self.add_recording_file)
        recordings_buttons.addWidget(self.import_button)
        
        # 删除按钮
        self.delete_button = QPushButton("删除选中")
        self.delete_button.clicked.connect(self.delete_selected_recordings)
        recordings_buttons.addWidget(self.delete_button)
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新列表")
        self.refresh_button.clicked.connect(self.refresh_recordings)
        recordings_buttons.addWidget(self.refresh_button)
        
        recordings_layout.addLayout(recordings_buttons)
        recordings_group.setLayout(recordings_layout)
        training_layout.addWidget(recordings_group)
        
        # 音频质量检查提示
        quality_tips = QLabel("提示: 为获得最佳效果，请使用高质量、背景噪音小的音频文件，建议时长总计超过2分钟")
        quality_tips.setWordWrap(True)
        quality_tips.setStyleSheet("color: #666; font-style: italic;")
        training_layout.addWidget(quality_tips)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        training_layout.addWidget(self.progress_bar)
        
        # 训练状态
        self.status_label = QLabel("")
        training_layout.addWidget(self.status_label)
        
        # 训练按钮
        self.train_button = QPushButton(self.i18n.translate("start_training"))
        self.train_button.clicked.connect(self.train_voice)
        training_layout.addWidget(self.train_button)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        self.setLayout(layout)
        
        # 初始化完成后刷新录音列表
        QTimer.singleShot(100, self.refresh_recordings)
    
    def refresh_voice_list(self):
        """刷新语音列表"""
        if not self.tts_engine:
            return
        
        # 获取语音列表
        voices = self.tts_engine.list_custom_voices()
        current_voice = self.tts_engine.get_current_voice()
        
        # 更新下拉列表
        self.voice_selector.clear()
        for voice in voices:
            self.voice_selector.addItem(voice)
        
        # 设置当前选中项
        index = self.voice_selector.findText(current_voice)
        if index >= 0:
            self.voice_selector.setCurrentIndex(index)
        
        # 更新列表控件
        self.recordings_list.clear()
        for voice in voices:
            self.recordings_list.addItem(voice)
    
    def change_voice(self, voice_name):
        """切换语音"""
        if not self.tts_engine or not voice_name:
            return
        
        if self.tts_engine.load_custom_voice(voice_name):
            self.voiceChanged.emit(voice_name)
    
    def test_voice(self):
        """测试当前语音"""
        if not self.tts_engine:
            return
        
        test_text = self.i18n.translate("voice_test_text")
        self.tts_engine.text_to_speech(test_text)
    
    def select_audio_files(self):
        """选择音频文件"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter(self.i18n.translate("audio_file_filter"))
        
        if file_dialog.exec():
            self.audio_files = file_dialog.selectedFiles()
            self.file_count_label.setText(f"{len(self.audio_files)} {self.i18n.translate('files_selected')}")
            
            # 检查是否有选择的文件，并激活训练按钮
            self.train_button.setEnabled(len(self.audio_files) > 0 and self.voice_name_input.text().strip() != "")
            
            # 显示所选文件的总时长（如果可以的话）
            try:
                from pydub import AudioSegment
                total_duration = 0
                for audio_file in self.audio_files:
                    try:
                        audio = AudioSegment.from_file(audio_file)
                        total_duration += len(audio) / 1000  # 转换为秒
                    except:
                        pass
                    
                if total_duration > 0:
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    self.file_count_label.setText(
                        f"{len(self.audio_files)} {self.i18n.translate('files_selected')} (总时长: {minutes}分{seconds}秒)"
                    )
            except ImportError:
                # 如果无法导入pydub，则忽略时长计算
                pass
    
    def train_voice(self):
        """训练声音模型"""
        # 首先检查TTS引擎是否正常
        if not self.tts_engine or not self.tts_engine.is_loaded():
            # 提示用户需要安装依赖
            reply = QMessageBox.question(
                self, 
                "TTS模型未加载", 
                "训练功能需要TTS模型支持，但当前未加载模型。\n\n是否要安装必要依赖并加载TTS模型？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 启动依赖安装过程
                self.install_tts_dependencies()
            return
        
        # 获取语音名称
        voice_name = self.voice_name_input.text().strip()
        if not voice_name:
            QMessageBox.warning(self, "提示", "请输入自定义语音名称")
            return
        
        # 检查名称合法性 (避免特殊字符)
        import re
        if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$', voice_name):
            QMessageBox.warning(self, "提示", "语音名称只能包含字母、数字、下划线和中文")
            return
        
        # 获取选定的录音文件
        selected_items = self.recordings_list.selectedItems()
        if not selected_items:
            # 尝试刷新列表
            self.refresh_recordings()
            
            # 查看是否有文件但未选择
            if self.recordings_list.count() > 0:
                QMessageBox.warning(self, "提示", "请选择要用于训练的录音文件")
            else:
                # 提示用户录制或导入录音
                response = QMessageBox.question(
                    self, 
                    "未找到录音文件", 
                    "没有找到可用于训练的录音文件。是否要录制新的语音样本？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if response == QMessageBox.Yes:
                    self.record_audio()
                else:
                    # 提示导入外部文件
                    import_response = QMessageBox.question(
                        self,
                        "导入录音文件",
                        "是否要从其他位置导入已有的录音文件？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if import_response == QMessageBox.Yes:
                        self.add_recording_file()
            return
        
        # 收集所有选定的录音文件路径
        recording_files = []
        for item in selected_items:
            file_path = item.data(Qt.UserRole)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                recording_files.append(file_path)
            else:
                print(f"警告: 文件不存在或为空: {file_path}")
        
        if not recording_files:
            QMessageBox.warning(self, "提示", "所选的录音文件无效")
            return
        
        # 显示确认对话框
        confirm_msg = f"您将使用 {len(recording_files)} 个录音文件训练自定义语音 '{voice_name}'。\n\n"
        confirm_msg += "训练过程可能需要几分钟，取决于录音文件数量和长度。\n"
        confirm_msg += "请确认开始训练？"
        
        reply = QMessageBox.question(
            self, 
            "确认训练", 
            confirm_msg, 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 显示训练进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("准备训练...")
        self.train_button.setEnabled(False)
        
        # 创建信号对象用于线程间通信
        from PySide6.QtCore import QObject, Signal
        
        class TrainingSignals(QObject):
            progress = Signal(int, str)
            error = Signal(str)
            completed = Signal()
        
        signals = TrainingSignals()
        
        # 连接信号和槽函数
        signals.progress.connect(self.update_training_progress)
        signals.error.connect(self.show_training_error)
        signals.completed.connect(self.training_completed)
        
        # 定义进度回调函数
        def update_progress(progress, message=None):
            if progress < 0:  # 错误状态
                signals.error.emit(message if message else "训练失败")
                return
            
            signals.progress.emit(progress, message if message else f"训练中... {progress}%")
            
            if progress >= 100:  # 训练完成
                signals.completed.emit()
        
        # 在后台线程中执行训练
        def training_thread():
            try:
                # 获取训练参数
                epochs = self.epochs_input.value()
                learning_rate = float(self.learning_rate_combo.currentText())
                
                # 设置训练参数
                train_params = {
                    'epochs': epochs,
                    'learning_rate': learning_rate
                }
                
                # 执行训练
                success = self.tts_engine.train_custom_voice(
                    voice_name, 
                    recording_files,
                    progress_callback=update_progress
                )
                
                # 训练完成，更新UI
                if not success and update_progress:
                    update_progress(-1, "训练失败，请查看日志获取详细信息")
            except Exception as e:
                # 显示错误信息
                signals.error.emit(str(e))
                import traceback
                traceback.print_exc()
        
        # 保存信号对象，防止被垃圾回收
        self._training_signals = signals
        
        # 启动训练线程
        thread = threading.Thread(target=training_thread)
        thread.daemon = True
        thread.start()
    
    @Slot(int, str)
    def update_training_progress(self, progress, message):
        """更新训练进度（作为槽函数被调用）"""
        try:
            self.progress_bar.setValue(progress)
            self.progress_bar.setVisible(True)
            self.status_label.setText(message)
            
            # 如果进度完成，恢复按钮状态
            if progress >= 100:
                self.train_button.setEnabled(True)
        except Exception as e:
            print(f"更新进度失败: {e}")

    @Slot(str)
    def show_training_error(self, error_message):
        """显示训练错误（作为槽函数被调用）"""
        try:
            # 显示错误信息
            self.status_label.setText(f"错误: {error_message}")
            self.progress_bar.setVisible(False)
            self.train_button.setEnabled(True)
            
            # 弹出错误对话框
            QMessageBox.critical(
                self,
                "训练失败",
                f"训练语音模型失败: \n\n{error_message}"
            )
        except Exception as e:
            print(f"显示错误消息失败: {e}")

    @Slot()
    def training_completed(self):
        """训练完成后的处理（作为槽函数被调用）"""
        try:
            # 更新UI状态
            self.progress_bar.setValue(100)
            self.status_label.setText("训练完成！")
            self.train_button.setEnabled(True)
            
            # 刷新语音列表
            self.refresh_voice_list()
            
            # 提示用户
            QMessageBox.information(
                self,
                "训练完成",
                f"'{self.voice_name_input.text()}'语音训练完成！\n\n您现在可以在测试功能中使用此语音。"
            )
        except Exception as e:
            print(f"处理训练完成事件失败: {e}")
    
    def update_manage_buttons(self):
        """更新管理按钮状态"""
        selected_items = self.recordings_list.selectedItems()
        
        # 只有选中了非默认语音才能删除
        enable_delete = len(selected_items) > 0 and selected_items[0].text() != "default"
        self.delete_button.setEnabled(enable_delete)
    
    def delete_voice(self):
        """删除选中的自定义语音"""
        selected_items = self.recordings_list.selectedItems()
        if not selected_items:
            return
        
        voice_name = selected_items[0].text()
        if voice_name == "default":
            return  # 默认语音不能删除
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            self.i18n.translate("confirm_delete"),
            self.i18n.translate("delete_voice_confirm").format(voice_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 删除语音目录
            import shutil
            voice_path = os.path.join(self.tts_engine.custom_voices_dir, voice_name)
            if os.path.exists(voice_path):
                shutil.rmtree(voice_path)
            
            # 如果删除的是当前使用的语音，切换回默认语音
            if voice_name == self.tts_engine.get_current_voice():
                self.tts_engine.load_custom_voice("default")
            
            # 刷新列表
            self.refresh_voice_list()
            
            QMessageBox.information(
                self,
                self.i18n.translate("success"),
                self.i18n.translate("delete_success")
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                self.i18n.translate("error"),
                f"{self.i18n.translate('delete_failed')}: {str(e)}"
            )
    
    def record_audio(self):
        """录制音频按钮点击事件"""
        # 检查是否已设置语音名称
        voice_name = self.voice_name_input.text().strip()
        if not voice_name:
            QMessageBox.warning(
                self,
                "提示",
                "请先输入自定义语音名称"
            )
            return
        
        # 创建录音对话框
        dialog = RecordingDialog(self, voice_name)
        if dialog.exec():
            # 如果录音成功，添加到文件列表
            if hasattr(dialog, 'saved_file') and dialog.saved_file and os.path.exists(dialog.saved_file):
                if not hasattr(self, 'audio_files'):
                    self.audio_files = []
                
                # 添加到训练文件列表
                self.audio_files.append(dialog.saved_file)
                self.file_count_label.setText(f"{len(self.audio_files)} {self.i18n.translate('files_selected')}")
                
                # 启用训练按钮
                self.train_button.setEnabled(True)
                
                # 显示成功消息
                QMessageBox.information(
                    self,
                    "录音成功",
                    f"录音已保存到: {dialog.saved_file}\n并添加到训练列表中"
                )
            else:
                QMessageBox.warning(
                    self,
                    "录音失败",
                    "未能成功保存录音文件，请重试"
                )

    def refresh_recordings(self):
        """刷新录音文件列表"""
        self.recordings_list.clear()
        
        # 确保录音路径存在
        voice_name = self.voice_name_input.text().strip()
        if not voice_name:
            voice_name = "default"
        
        # 保存当前语音名称以便后续使用
        self.voice_name = voice_name
        
        voice_dir = os.path.join('data', 'voices', voice_name, 'audio')
        if not os.path.exists(voice_dir):
            os.makedirs(voice_dir, exist_ok=True)
            print(f"创建录音目录: {voice_dir}")
            return
        
        # 扫描录音文件
        recordings = []
        for file in os.listdir(voice_dir):
            if file.lower().endswith('.wav'):
                file_path = os.path.join(voice_dir, file)
                
                # 检查文件大小，确保不是空文件
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > 1000:  # 至少1KB
                        # 获取文件创建时间
                        created_time = os.path.getctime(file_path)
                        recordings.append((file, file_path, created_time))
                    else:
                        print(f"跳过小文件: {file_path}, 大小: {file_size} 字节")
                except Exception as e:
                    print(f"检查文件时出错: {file_path}, {e}")
        
        if not recordings:
            print(f"警告: 在录音目录 {voice_dir} 中未找到有效的WAV文件")
            return
        
        # 按创建时间倒序排列，最新的在前面
        recordings.sort(key=lambda x: x[2], reverse=True)
        
        # 添加到列表
        for recording, path, _ in recordings:
            try:
                duration = self.get_audio_duration(path)
                size_kb = os.path.getsize(path) / 1024
                
                # 创建列表项
                item = QListWidgetItem(f"{recording} ({size_kb:.1f} KB, {duration:.1f}秒)")
                item.setData(Qt.UserRole, path)  # 存储完整路径
                self.recordings_list.addItem(item)
            except Exception as e:
                print(f"添加文件到列表失败: {path}, {e}")
        
        # 自动选择第一个文件
        if self.recordings_list.count() > 0:
            self.recordings_list.setCurrentRow(0)
        
        print(f"发现 {len(recordings)} 个录音文件在 {voice_dir}")
        
        # 如果有录音，启用训练按钮
        self.train_button.setEnabled(self.recordings_list.count() > 0)

    def get_audio_duration(self, file_path):
        """获取音频文件时长（秒）"""
        try:
            import wave
            with wave.open(file_path, 'rb') as wf:
                # 获取帧率和总帧数
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                duration = nframes / float(framerate)
                return duration
        except Exception as e:
            print(f"获取音频时长失败: {file_path}, {e}")
            return 0.0

    def convert_audio_format(self, input_file, output_file=None, target_rate=16000, target_channels=1):
        """将音频转换为模型训练所需格式"""
        if output_file is None:
            # 在原文件名基础上添加标记
            filename, ext = os.path.splitext(input_file)
            output_file = f"{filename}_converted{ext}"
        
        try:
            # 使用ffmpeg或pydub进行转换
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_wav(input_file)
                
                # 转换为单声道
                if audio.channels != target_channels:
                    audio = audio.set_channels(target_channels)
                    
                # 转换采样率
                if audio.frame_rate != target_rate:
                    audio = audio.set_frame_rate(target_rate)
                    
                # 导出为WAV
                audio.export(output_file, format="wav")
                print(f"转换完成: {output_file}")
                return output_file
            except ImportError:
                # 如果没有pydub，尝试使用ffmpeg命令行
                import subprocess
                cmd = ["ffmpeg", "-i", input_file, "-ac", str(target_channels), 
                       "-ar", str(target_rate), "-y", output_file]
                subprocess.run(cmd, check=True)
                print(f"使用ffmpeg转换完成: {output_file}")
                return output_file
        except Exception as e:
            print(f"转换音频格式失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def add_recording_file(self):
        """导入外部音频文件作为录音数据"""
        # 获取语音名称
        voice_name = self.voice_name_input.text().strip()
        if not voice_name:
            QMessageBox.warning(self, "提示", "请先输入自定义语音名称")
            return
        
        # 保存当前语音名称以便后续使用
        self.voice_name = voice_name
        
        # 打开文件选择对话框
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            "",
            "WAV文件 (*.wav);;所有文件 (*.*)"
        )
        
        if not files:
            return
        
        # 确保目标目录存在
        voice_dir = os.path.join('data', 'voices', voice_name, 'audio')
        os.makedirs(voice_dir, exist_ok=True)
        
        # 复制文件到目标目录
        import shutil
        imported_count = 0
        
        for file_path in files:
            try:
                # 生成目标文件名
                filename = os.path.basename(file_path)
                # 如果文件名已存在，添加时间戳
                if os.path.exists(os.path.join(voice_dir, filename)):
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{int(time.time())}{ext}"
                    
                dest_path = os.path.join(voice_dir, filename)
                
                # 复制文件
                shutil.copy2(file_path, dest_path)
                print(f"已导入音频文件: {file_path} -> {dest_path}")
                imported_count += 1
            except Exception as e:
                print(f"导入音频文件失败: {file_path}, {e}")
        
        # 刷新列表
        self.refresh_recordings()
        
        if imported_count > 0:
            QMessageBox.information(
                self,
                "导入成功",
                f"成功导入 {imported_count} 个音频文件"
            )

    def install_tts_dependencies(self):
        """安装TTS依赖项并重新加载模型"""
        try:
            # 显示进度对话框（带取消按钮）
            progress = QMessageBox(self)
            progress.setWindowTitle("正在准备TTS模型")
            progress.setText("正在安装依赖和准备模型，请稍候...")
            progress.setStandardButtons(QMessageBox.Cancel)
            progress.setIcon(QMessageBox.Information)
            progress.setDefaultButton(QMessageBox.Cancel)
            
            # 创建和显示对话框，但不阻塞UI线程
            progress.show()
            
            # 在后台线程中执行安装
            def install_thread():
                try:
                    # 获取正在运行的Python解释器路径
                    import sys
                    python = sys.executable
                    
                    # 先检查哪些依赖已经安装
                    needed_deps = []
                    all_deps = [
                        "addict", 
                        "accelerate", 
                        "transformers>=4.30.0", 
                        "transformers_stream_generator",
                        "torch>=2.0.0",
                        "numpy",
                        "soundfile",
                        "tensorboard",
                        "librosa",
                        "GitPython",
                        "requests"
                    ]
                    
                    # 检查依赖是否已安装
                    progress.setText("检查已安装的依赖...")
                    for dep in all_deps:
                        dep_name = dep.split('>=')[0] if '>=' in dep else dep
                        try:
                            importlib.import_module(dep_name)
                            print(f"依赖已安装: {dep_name}")
                        except ImportError:
                            needed_deps.append(dep)
                            print(f"依赖未安装: {dep_name}，将进行安装")
                    
                    # 更新对话框文本
                    if needed_deps:
                        progress.setText(f"需要安装 {len(needed_deps)} 个依赖...")
                    else:
                        progress.setText("所有依赖已安装，正在加载模型...")
                    
                    # 安装依赖
                    import subprocess
                    for i, dep in enumerate(needed_deps):
                        # 检查是否取消
                        if not progress.isVisible():
                            return False
                        
                        # 更新进度文本
                        progress.setText(f"正在安装: {dep} ({i+1}/{len(needed_deps)})...")
                        
                        try:
                            subprocess.check_call([python, "-m", "pip", "install", dep, "--quiet"])
                            print(f"安装依赖: {dep}")
                        except Exception as e:
                            print(f"安装依赖失败: {dep}, {e}")
                    
                    if needed_deps:
                        print("成功安装所需依赖")
                    
                    # 尝试更新modelscope
                    progress.setText("正在更新modelscope...")
                    try:
                        subprocess.check_call([python, "-m", "pip", "install", "modelscope", "--upgrade", "--quiet"])
                        print("已更新modelscope库")
                    except:
                        print("更新modelscope失败，继续使用现有版本")
                    
                    # 重新加载TTS引擎
                    progress.setText("正在加载TTS模型...")
                    if self.assistant and hasattr(self.assistant, 'tts_engine'):
                        # 重新初始化TTS引擎
                        self.assistant.tts_engine.initialize()
                        self.tts_engine = self.assistant.tts_engine
                        
                        # 检查是否成功加载
                        if self.tts_engine.is_loaded():
                            # 关闭对话框（成功）
                            progress.setStandardButtons(QMessageBox.Ok)
                            progress.setText("TTS模型加载成功！")
                            progress.setIcon(QMessageBox.Information)
                            print("TTS模型重新加载成功")
                            return True
                        else:
                            # 更新对话框（失败）
                            progress.setStandardButtons(QMessageBox.Ok)
                            progress.setText("依赖已安装，但模型加载失败。\n请重启应用程序后再试。")
                            progress.setIcon(QMessageBox.Warning)
                            print("TTS模型重新加载失败，需要重启应用")
                            return False
                except Exception as e:
                    # 出错时更新对话框
                    if progress.isVisible():
                        progress.setStandardButtons(QMessageBox.Ok)
                        progress.setText(f"安装依赖时出错: {str(e)}")
                        progress.setIcon(QMessageBox.Critical)
                    print(f"安装TTS依赖时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            
            # 在后台线程中运行安装
            install_thread = threading.Thread(target=install_thread)
            install_thread.daemon = True
            install_thread.start()
            
            return True  # 返回True表示安装过程已启动
        except Exception as e:
            print(f"启动安装过程失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_selected_recordings(self):
        """删除选定的录音文件"""
        selected_items = self.recordings_list.selectedItems()
        if not selected_items:
            return
        
        # 确认是否删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除选中的 {len(selected_items)} 个录音文件吗？\n此操作不可恢复。", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 删除文件
        for item in selected_items:
            file_path = item.data(Qt.UserRole)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"已删除文件: {file_path}")
                else:
                    print(f"文件不存在: {file_path}")
            except Exception as e:
                print(f"删除文件失败: {file_path}, {e}")
            
        # 刷新列表
        self.refresh_recordings()

class RecordingDialog(QDialog):
    """录音对话框"""
    
    def __init__(self, parent, voice_name):
        super().__init__(parent)
        self.voice_name = voice_name
        self.recording = False
        self.parent = parent  # 保存父窗口引用
        self.saved_file = None
        
        # 生成训练文案
        self.training_texts = self.generate_training_text()
        self.current_text_index = 0
        
        self.init_ui()
        self.setup_recorder()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("录制训练音频")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # 说明文字
        instructions = QLabel("请朗读下面的文本进行录音。朗读时请保持自然的语调和速度。")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # 训练文案显示
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setMinimumHeight(150)
        self.text_display.setStyleSheet("font-size: 16px; background-color: #f9f9f9;")
        layout.addWidget(self.text_display)
        
        # 显示第一条训练文本
        self.show_current_text()
        
        # 录音控制区域
        controls_layout = QHBoxLayout()
        
        # 录音按钮
        self.record_button = QPushButton("开始录音")
        self.record_button.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.record_button)
        
        # 上一条/下一条文本按钮
        self.prev_button = QPushButton("上一条")
        self.prev_button.clicked.connect(self.show_prev_text)
        controls_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("下一条")
        self.next_button.clicked.connect(self.show_next_text)
        controls_layout.addWidget(self.next_button)
        
        layout.addLayout(controls_layout)
        
        # 录音状态
        self.status_label = QLabel("准备录音...")
        layout.addWidget(self.status_label)
        
        # 录音时长
        self.duration_label = QLabel("00:00")
        self.duration_label.setAlignment(Qt.AlignCenter)
        self.duration_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.duration_label)
        
        # 确定和取消按钮
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("保存并关闭")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setEnabled(False)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # 设置计时器
        self.timer = QTimer()
        self.timer.setInterval(1000)  # 1秒
        self.timer.timeout.connect(self.update_duration)
        self.duration_seconds = 0
    
    def setup_recorder(self):
        """设置录音机"""
        try:
            # 确保目录存在
            voice_dir = os.path.join('data', 'voices', self.voice_name, 'audio')
            os.makedirs(voice_dir, exist_ok=True)
            
            # 设置初始输出文件
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.output_file = os.path.join(voice_dir, f"recording_{timestamp}.wav")
            
            # 优先使用PyAudio (更可靠)
            if PYAUDIO_AVAILABLE:
                print(f"使用PyAudio录音，输出文件: {self.output_file}")
                self.recorder = PyAudioRecorder(self.output_file)
                self.use_pyaudio = True
            else:
                # 回退到PySide6的录音功能
                print("PyAudio未安装，使用PySide6录音功能")
                
                # 初始化录音设备
                self.audio_input = QAudioInput()
                self.recorder = QMediaRecorder()
                self.capture_session = QMediaCaptureSession()
                
                # 检查和设置默认音频输入设备
                available_inputs = QMediaDevices.audioInputs()
                if available_inputs:
                    self.audio_input.setDevice(available_inputs[0])
                    print(f"使用音频输入设备: {available_inputs[0].description()}")
                else:
                    print("警告: 未找到音频输入设备")
                
                self.capture_session.setAudioInput(self.audio_input)
                self.capture_session.setRecorder(self.recorder)
                
                # 使用基本配置
                try:
                    self.recorder.setQuality(QMediaRecorder.NormalQuality)
                    self.recorder.setEncodingMode(QMediaRecorder.ConstantQualityEncoding)
                except:
                    pass
                
                # 设置输出文件
                self.recorder.setOutputLocation(self.output_file)
                
                # 连接信号
                self.recorder.recorderStateChanged.connect(self.recorder_state_changed)
                self.recorder.errorOccurred.connect(self.recorder_error)
                
                self.use_pyaudio = False
            
            # 创建计时器
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_duration)
            self.timer.setInterval(1000)  # 每秒更新一次
            
        except Exception as e:
            print(f"设置录音机失败: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"错误: {str(e)}")
    
    def toggle_recording(self):
        """切换录音状态"""
        if self.recording:
            # 停止录音
            if hasattr(self, 'use_pyaudio') and self.use_pyaudio:
                self.recorder.stop()
            else:
                self.recorder.stop()
            
            self.record_button.setText("开始录音")
            self.recording = False
            self.timer.stop()
            
            # 添加延迟，确保文件被完全写入
            QTimer.singleShot(500, self.check_recording_file)
        else:
            # 开始录音
            try:
                # 确保音频输出目录存在
                voice_dir = os.path.join('data', 'voices', self.voice_name, 'audio')
                os.makedirs(voice_dir, exist_ok=True)
                
                # 设置输出文件
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                self.output_file = os.path.join(voice_dir, f"recording_{timestamp}.wav")
                
                if hasattr(self, 'use_pyaudio') and self.use_pyaudio:
                    # 使用PyAudio录音
                    self.recorder.output_file = self.output_file
                    self.recorder.record()
                else:
                    # 使用PySide6录音
                    self.recorder.setOutputLocation(self.output_file)
                    self.recorder.record()
                
                print(f"开始录音，保存到: {self.output_file}")
                self.record_button.setText("停止录音")
                self.recording = True
                self.duration_seconds = 0
                self.duration_label.setText("00:00")
                self.timer.start()
                self.status_label.setText("正在录音...")
            except Exception as e:
                self.status_label.setText(f"录音失败: {str(e)}")
                import traceback
                traceback.print_exc()
    
    def check_recording_file(self):
        """检查录音文件是否正确保存并符合要求"""
        try:
            # 保存录音文件
            self.saved_file = self.output_file
            print(f"检查录音文件: {self.saved_file}")
            
            # 如果使用PyAudio，添加额外等待以确保文件写入
            if hasattr(self, 'use_pyaudio') and self.use_pyaudio:
                # 确保录音线程已完全停止并写入文件
                time.sleep(0.5)  # 等待文件写入完成
            
            # 确保录音文件有效
            if os.path.exists(self.saved_file):
                file_size = os.path.getsize(self.saved_file)
                print(f"录音文件存在，大小: {file_size} 字节")
                
                if file_size > 0:
                    # 检查音频格式是否符合要求
                    try:
                        import wave
                        with wave.open(self.saved_file, 'rb') as wf:
                            channels = wf.getnchannels()
                            sample_width = wf.getsampwidth()
                            frame_rate = wf.getframerate()
                            print(f"音频信息：通道数 {channels}，采样位深 {sample_width}，采样率 {frame_rate} Hz")
                            
                            # 检查是否符合训练要求（一般要求单声道、16位深度、16kHz或以上采样率）
                            if channels != 1:
                                print(f"警告：音频为{channels}声道，训练可能需要单声道")
                            if frame_rate < 16000:
                                print(f"警告：采样率 {frame_rate} Hz 较低，建议使用 16kHz 或以上")
                    except Exception as e:
                        print(f"检查音频格式时出错: {e}")
                    
                    # 保存录音相关数据
                    if self.save_recording_data():
                        self.save_button.setEnabled(True)
                        self.status_label.setText("录音已完成并保存")
                        print(f"录音数据已保存: {self.saved_file}")
                        return True
                    else:
                        self.status_label.setText("录音已完成，但保存数据失败")
                else:
                    self.status_label.setText("录音文件为空，请重试")
                    print("警告: 录音文件存在但为空")
            else:
                self.status_label.setText("未找到录音文件，请重试")
                
                # 搜索目录中的其他录音文件
                try:
                    dir_path = os.path.dirname(self.saved_file)
                    if os.path.exists(dir_path):
                        files = os.listdir(dir_path)
                        recent_files = [f for f in files if f.endswith('.wav') and 'recording_' in f]
                        if recent_files:
                            print(f"目录中存在其他录音文件: {recent_files}")
                            
                            # 尝试使用最新的录音文件
                            recent_files.sort(reverse=True)  # 按名称排序，最新在前
                            newest_file = os.path.join(dir_path, recent_files[0])
                            if os.path.exists(newest_file) and os.path.getsize(newest_file) > 0:
                                print(f"使用最新的录音文件: {newest_file}")
                                self.saved_file = newest_file
                                if self.save_recording_data():
                                    self.save_button.setEnabled(True)
                                    self.status_label.setText("使用最新录音文件")
                                    return
                        else:
                            print(f"目录中没有录音文件: {dir_path}")
                    else:
                        print(f"录音目录不存在: {dir_path}")
                except Exception as e:
                    print(f"搜索录音文件时出错: {e}")
                    
                # 尝试强制创建一个空白文件进行测试
                try:
                    test_file = os.path.join(os.path.dirname(self.saved_file), "test_write.txt")
                    with open(test_file, 'w') as f:
                        f.write("测试写入权限")
                    print(f"测试文件写入成功: {test_file}")
                    if os.path.exists(test_file):
                        os.remove(test_file)
                except Exception as e:
                    print(f"测试文件写入失败: {e}")
                    self.status_label.setText(f"可能是权限问题，无法写入文件: {str(e)}")
        except Exception as e:
            self.status_label.setText(f"检查录音文件失败: {str(e)}")
            print(f"检查录音文件时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return False
    
    def recorder_state_changed(self, state):
        """录音机状态变化"""
        if state == QMediaRecorder.RecordingState:
            self.status_label.setText("正在录音...")
        elif state == QMediaRecorder.StoppedState:
            self.status_label.setText("录音已停止")
    
    def recorder_error(self, error, error_string):
        """录音机错误"""
        print(f"录音错误 ({error}): {error_string}")  # 添加详细日志
        self.status_label.setText(f"录音错误: {error_string}")
        
        # 尝试识别常见问题
        if "permission" in error_string.lower():
            self.status_label.setText("录音权限被拒绝，请检查系统设置")
        elif "device" in error_string.lower():
            self.status_label.setText("录音设备不可用，请检查麦克风连接")
        elif "format" in error_string.lower():
            self.status_label.setText("不支持的录音格式，尝试修改设置")
    
    def update_duration(self):
        """更新录音时长"""
        self.duration_seconds += 1
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")
    
    def show_current_text(self):
        """显示当前训练文本"""
        if 0 <= self.current_text_index < len(self.training_texts):
            self.text_display.setText(self.training_texts[self.current_text_index])
    
    def show_next_text(self):
        """显示下一条训练文本"""
        if self.current_text_index < len(self.training_texts) - 1:
            self.current_text_index += 1
            self.show_current_text()
    
    def show_prev_text(self):
        """显示上一条训练文本"""
        if self.current_text_index > 0:
            self.current_text_index -= 1
            self.show_current_text()
    
    def generate_training_text(self):
        """生成训练文本"""
        # 预设一些适合语音训练的句子，覆盖不同音调和语境
        training_texts = [
            "这是一个语音合成系统测试，用于创建自然流畅的中文语音。",
            "人工智能技术正在快速发展，让我们的生活变得更加便捷。",
            "春天来了，花儿开放，蜜蜂在花丛中忙碌地采集花粉。",
            "未来的科技将会更加智能化，能够理解人类的需求和情感。",
            "声音是人类交流的重要媒介，通过声音我们可以表达情感和思想。",
            "我喜欢在安静的下午阅读一本好书，沉浸在知识的海洋中。",
            "山间的小溪流水潺潺，鸟儿在林中歌唱，构成了一幅美丽的画卷。",
            "你好吗？今天天气真不错，阳光明媚，微风拂面。",
            "请问现在几点了？我想我可能需要调整一下日程安排。",
            "这个问题有点复杂，让我们一步一步地分析和解决它。"
        ]
        
        # 随机打乱顺序，增加训练多样性
        random.shuffle(training_texts)
        return training_texts
    
    def save_recording_data(self):
        """保存录音数据和文本"""
        try:
            # 确保目录存在
            voice_name = self.voice_name
            voice_dir = os.path.join('data', 'voices', voice_name)
            os.makedirs(voice_dir, exist_ok=True)
            
            # 创建文本数据目录
            texts_dir = os.path.join(voice_dir, 'texts')
            os.makedirs(texts_dir, exist_ok=True)
            
            # 保存当前使用的训练文本
            text_content = self.text_display.toPlainText()
            text_file = os.path.join(texts_dir, f"{os.path.basename(self.saved_file).split('.')[0]}.txt")
            
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            # 创建训练元数据文件
            metadata_file = os.path.join(voice_dir, 'metadata.json')
            
            # 读取现有元数据或创建新的
            metadata = {}
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    metadata = {"recordings": []}
            else:
                metadata = {"recordings": []}
            
            # 添加新的录音信息
            recording_info = {
                "audio_file": os.path.basename(self.saved_file),
                "text_file": os.path.basename(text_file),
                "text": text_content,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            metadata["recordings"].append(recording_info)
            
            # 保存元数据
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"成功保存录音数据: {os.path.basename(self.saved_file)}")
            return True
        except Exception as e:
            print(f"保存录音数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def accept(self):
        """用户接受对话框"""
        if hasattr(self, 'saved_file') and os.path.exists(self.saved_file):
            # 如果存在有效的录音文件
            super().accept()
        else:
            QMessageBox.warning(
                self,
                "警告",
                "请先录制并停止录音，然后再保存"
            )

    def save_recording(self):
        """保存录音，并通知父窗口刷新文件列表"""
        # ... 现有保存代码 ...
        
        # 通知父窗口刷新文件列表
        if self.parent and hasattr(self.parent, 'refresh_recordings'):
            self.parent.refresh_recordings()

# 添加PyAudio录音类
class PyAudioRecorder:
    """使用PyAudio的录音器实现"""
    
    def __init__(self, output_file):
        self.output_file = output_file
        self.recording = False
        self.frames = []
        self.pyaudio = pyaudio.PyAudio()
        self.stream = None
        
        # 设置参数 - 使用标准参数提高兼容性
        self.chunk = 1024
        self.format = pyaudio.paInt16  # 16位PCM
        self.channels = 1  # 单声道
        self.rate = 44100  # 44.1kHz 或 使用 16000 可能更适合语音模型
        
        print(f"PyAudio录音器初始化，输出文件: {self.output_file}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(self.output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"创建录音输出目录: {output_dir}")
    
    def record(self):
        """开始录音"""
        if self.recording:
            return
            
        self.frames = []
        try:
            self.stream = self.pyaudio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            self.recording = True
            
            # 开始录音线程
            import threading
            self.thread = threading.Thread(target=self._record_thread)
            self.thread.daemon = True
            self.thread.start()
            
            print(f"PyAudio开始录音，线程ID: {self.thread.ident}")
        except Exception as e:
            print(f"PyAudio录音启动失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _record_thread(self):
        """录音线程"""
        print("PyAudio录音线程启动")
        try:
            while self.recording:
                try:
                    data = self.stream.read(self.chunk)
                    self.frames.append(data)
                except Exception as e:
                    print(f"读取音频数据时出错: {e}")
                    break
            print(f"PyAudio录音线程结束，收集了 {len(self.frames)} 帧数据")
        except Exception as e:
            print(f"PyAudio录音线程异常: {e}")
    
    def stop(self):
        """停止录音"""
        if not self.recording:
            return
            
        print("停止PyAudio录音")
        self.recording = False
        
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # 等待录音线程结束
            if hasattr(self, 'thread') and self.thread.is_alive():
                self.thread.join(timeout=1.0)
                print("录音线程已结束")
            
            # 保存WAV文件
            if self.frames:
                try:
                    print(f"开始保存WAV文件: {self.output_file}")
                    wf = wave.open(self.output_file, 'wb')
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.pyaudio.get_sample_size(self.format))
                    wf.setframerate(self.rate)
                    wf.writeframes(b''.join(self.frames))
                    wf.close()
                    
                    # 确认文件已保存
                    if os.path.exists(self.output_file):
                        size = os.path.getsize(self.output_file)
                        print(f"WAV文件已保存: {self.output_file}，大小: {size} 字节")
                    else:
                        print(f"错误: WAV文件保存失败，文件不存在: {self.output_file}")
                except Exception as e:
                    print(f"保存WAV文件时出错: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("警告: 没有录音数据可保存")
        except Exception as e:
            print(f"停止录音时出错: {e}")
            import traceback
            traceback.print_exc() 