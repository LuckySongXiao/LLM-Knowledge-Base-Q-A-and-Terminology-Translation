import os
import json

class TTSEngine:
    """语音合成引擎 (简化版 - 无实际功能)"""
    
    def __init__(self, settings):
        self.settings = settings
        self.model_path = settings.get('tts_model_path', '')
        
        # 规范化模型路径
        if self.model_path:
            print(f"初始化TTS引擎，模型路径: {self.model_path}")
        else:
            print("警告: TTS模型路径未设置")
        
        # 保留必要的属性以保持接口一致
        self.custom_voice_name = "default"
        self.custom_voices_dir = os.path.join('data', 'voices')
        if not os.path.exists(self.custom_voices_dir):
            os.makedirs(self.custom_voices_dir)
            
        # 模拟TTS初始化成功
        print("TTS引擎初始化完成（模拟模式）")
        
    def load_models(self):
        """加载TTS模型 (模拟)"""
        print("TTS模型加载成功（模拟模式）")
        return True
        
    def load_voice_settings(self):
        """加载语音设置 (模拟)"""
        voice_settings_path = os.path.join(self.custom_voices_dir, 'settings.json')
        if os.path.exists(voice_settings_path):
            try:
                with open(voice_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.custom_voice_name = settings.get('current_voice', 'default')
            except Exception as e:
                print(f"加载语音设置失败: {e}")
    
    def save_voice_settings(self):
        """保存语音设置 (模拟)"""
        voice_settings_path = os.path.join(self.custom_voices_dir, 'settings.json')
        try:
            with open(voice_settings_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'current_voice': self.custom_voice_name
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存语音设置失败: {e}")
    
    def synthesize(self, text, voice_name=None, output_path=None):
        """合成语音 (模拟)"""
        print(f"【模拟TTS】生成文本: '{text[:100]}...'")
        
        # 如果需要保存文件，创建一个空文件
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write("TTS模拟输出")
                print(f"已创建模拟音频文件: {output_path}")
            except Exception as e:
                print(f"创建模拟音频文件失败: {e}")
                
        return None  # 不返回实际波形
    
    def _play_speech(self, text=None, waveform=None):
        """播放语音 (模拟)"""
        print(f"【模拟TTS】播放文本: '{text[:100] if text else '(无文本)'}'")
        return True
    
    def _play_with_system_tts(self, text):
        """使用系统TTS播放 (模拟)"""
        print(f"【模拟系统TTS】播放文本: '{text[:100]}'")
        return True
    
    def speak_text(self, text, voice_name=None):
        """朗读文本 (模拟)"""
        if not text:
            return False
            
        print(f"【模拟TTS】朗读文本: '{text[:100]}...'")
        return True
    
    def list_custom_voices(self):
        """列出自定义语音 (模拟)"""
        return ["default", "simulated_voice"]
    
    def get_current_voice(self):
        """获取当前语音 (模拟) - 修复缺失方法"""
        return self.custom_voice_name
    
    def set_current_voice(self, voice_name):
        """设置当前语音 (模拟)"""
        print(f"【模拟TTS】设置当前语音: {voice_name}")
        self.custom_voice_name = voice_name
        self.save_voice_settings()
        return True
    
    def load_custom_voice(self, voice_name):
        """加载自定义语音 (模拟)"""
        print(f"【模拟TTS】加载语音: {voice_name}")
        self.custom_voice_name = voice_name
        return True
    
    def install_dependencies(self, silent=False):
        """安装TTS依赖 (模拟)"""
        print("【模拟TTS】跳过依赖安装")
        return True
        
    def train_custom_voice(self, voice_name, audio_files, progress_callback=None):
        """训练自定义语音 (模拟)"""
        print(f"【模拟TTS】训练自定义语音: {voice_name}, 使用{len(audio_files)}个音频文件")
        
        # 模拟训练进度
        if progress_callback:
            for i in range(0, 101, 10):
                progress_callback(i)
                import time
                time.sleep(0.1)
                
        return True
        
    def delete_custom_voice(self, voice_name):
        """删除自定义语音 (模拟)"""
        print(f"【模拟TTS】删除自定义语音: {voice_name}")
        if self.custom_voice_name == voice_name:
            self.custom_voice_name = "default"
            self.save_voice_settings()
        return True 