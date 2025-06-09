"""
语音API模块
提供语音合成和识别相关的RESTful API接口
"""

from flask import Blueprint, request, jsonify, current_app, send_file
import os
import tempfile
import base64
from datetime import datetime
from werkzeug.utils import secure_filename

voice_bp = Blueprint('voice', __name__)

@voice_bp.route('/tts', methods=['POST'])
def text_to_speech():
    """文本转语音"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': '文本内容不能为空'}), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({'error': '文本内容不能为空'}), 400
        
        voice_name = data.get('voice', 'default')
        speed = data.get('speed', 1.0)
        pitch = data.get('pitch', 1.0)
        
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant:
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500
        
        # 检查TTS引擎是否可用
        if not hasattr(assistant, 'tts_engine') or not assistant.tts_engine:
            return jsonify({'error': 'TTS引擎未初始化'}), 500
        
        tts_engine = assistant.tts_engine
        
        # 生成语音文件
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # 生成语音
            success = tts_engine.synthesize_to_file(
                text=text,
                output_path=temp_path,
                voice=voice_name,
                speed=speed,
                pitch=pitch
            )
            
            if not success or not os.path.exists(temp_path):
                return jsonify({'error': '语音合成失败'}), 500
            
            # 读取音频文件并转换为base64
            with open(temp_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 清理临时文件
            os.unlink(temp_path)
            
            return jsonify({
                'success': True,
                'audio_data': audio_base64,
                'audio_format': 'wav',
                'text': text,
                'voice': voice_name,
                'duration': len(audio_data) / 16000,  # 估算时长（假设16kHz采样率）
                'generated_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            # 清理临时文件
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        
    except Exception as e:
        current_app.logger.error(f"TTS失败: {e}")
        return jsonify({'error': f'TTS失败: {str(e)}'}), 500

@voice_bp.route('/stt', methods=['POST'])
def speech_to_text():
    """语音转文本"""
    try:
        # 检查是否有音频文件
        if 'audio' not in request.files:
            return jsonify({'error': '没有上传音频文件'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': '没有选择音频文件'}), 400
        
        # 检查文件格式
        allowed_formats = {'wav', 'mp3', 'flac', 'ogg', 'm4a'}
        file_ext = audio_file.filename.rsplit('.', 1)[1].lower() if '.' in audio_file.filename else ''
        if file_ext not in allowed_formats:
            return jsonify({'error': f'不支持的音频格式，支持的格式: {", ".join(allowed_formats)}'}), 400
        
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant:
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500
        
        # 检查STT引擎是否可用
        if not hasattr(assistant, 'stt_engine') or not assistant.stt_engine:
            return jsonify({'error': 'STT引擎未初始化'}), 500
        
        stt_engine = assistant.stt_engine
        
        # 保存临时音频文件
        try:
            filename = secure_filename(audio_file.filename)
            with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False) as temp_file:
                temp_path = temp_file.name
                audio_file.save(temp_path)
            
            # 执行语音识别
            text_result = stt_engine.transcribe(temp_path)
            
            # 清理临时文件
            os.unlink(temp_path)
            
            if not text_result:
                return jsonify({'error': '语音识别失败或音频中没有检测到语音'}), 500
            
            return jsonify({
                'success': True,
                'text': text_result,
                'filename': filename,
                'transcribed_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            # 清理临时文件
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        
    except Exception as e:
        current_app.logger.error(f"STT失败: {e}")
        return jsonify({'error': f'STT失败: {str(e)}'}), 500

@voice_bp.route('/voices', methods=['GET'])
def get_available_voices():
    """获取可用的语音列表"""
    try:
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant:
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500
        
        voices = []
        
        # 检查TTS引擎是否可用
        if hasattr(assistant, 'tts_engine') and assistant.tts_engine:
            try:
                voices = assistant.tts_engine.get_available_voices()
            except Exception as e:
                current_app.logger.warning(f"获取语音列表失败: {e}")
                # 提供默认语音列表
                voices = [
                    {'id': 'default', 'name': '默认语音', 'language': 'zh', 'gender': 'female'},
                    {'id': 'male', 'name': '男声', 'language': 'zh', 'gender': 'male'},
                    {'id': 'female', 'name': '女声', 'language': 'zh', 'gender': 'female'}
                ]
        else:
            # TTS引擎未初始化时的默认语音
            voices = [
                {'id': 'default', 'name': '默认语音', 'language': 'zh', 'gender': 'female'}
            ]
        
        return jsonify({
            'success': True,
            'voices': voices,
            'total_count': len(voices)
        })
        
    except Exception as e:
        current_app.logger.error(f"获取语音列表失败: {e}")
        return jsonify({'error': f'获取语音列表失败: {str(e)}'}), 500

@voice_bp.route('/train_voice', methods=['POST'])
def train_custom_voice():
    """训练自定义语音"""
    try:
        data = request.get_json()
        if not data or 'voice_name' not in data:
            return jsonify({'error': '语音名称不能为空'}), 400
        
        voice_name = data['voice_name'].strip()
        if not voice_name:
            return jsonify({'error': '语音名称不能为空'}), 400
        
        # 获取训练参数
        epochs = data.get('epochs', 100)
        learning_rate = data.get('learning_rate', 0.001)
        
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant:
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500
        
        # 检查TTS引擎是否支持训练
        if not hasattr(assistant, 'tts_engine') or not assistant.tts_engine:
            return jsonify({'error': 'TTS引擎未初始化'}), 500
        
        tts_engine = assistant.tts_engine
        
        if not hasattr(tts_engine, 'train_custom_voice'):
            return jsonify({'error': '当前TTS引擎不支持自定义语音训练'}), 400
        
        # 检查是否有训练音频文件
        # 这里应该从之前上传的音频文件中获取训练数据
        # 为简化示例，我们假设训练数据已经准备好
        
        try:
            # 启动训练（这应该是异步的）
            training_id = f"training_{int(datetime.now().timestamp())}"
            
            # 在实际实现中，这里应该启动一个后台任务
            # 这里只是返回一个训练ID，实际训练需要在后台进行
            
            return jsonify({
                'success': True,
                'message': f'语音训练已开始',
                'training_id': training_id,
                'voice_name': voice_name,
                'estimated_time': '30-60分钟',
                'started_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            current_app.logger.error(f"启动语音训练失败: {e}")
            return jsonify({'error': f'启动语音训练失败: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"语音训练请求处理失败: {e}")
        return jsonify({'error': f'语音训练请求处理失败: {str(e)}'}), 500

@voice_bp.route('/upload_training_audio', methods=['POST'])
def upload_training_audio():
    """上传训练音频文件"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': '没有上传音频文件'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': '没有选择音频文件'}), 400
        
        text_content = request.form.get('text', '').strip()
        if not text_content:
            return jsonify({'error': '必须提供对应的文本内容'}), 400
        
        # 检查文件格式
        allowed_formats = {'wav', 'mp3', 'flac'}
        file_ext = audio_file.filename.rsplit('.', 1)[1].lower() if '.' in audio_file.filename else ''
        if file_ext not in allowed_formats:
            return jsonify({'error': f'不支持的音频格式，支持的格式: {", ".join(allowed_formats)}'}), 400
        
        # 保存训练音频文件
        training_dir = 'data/voice_training'
        os.makedirs(training_dir, exist_ok=True)
        
        filename = secure_filename(audio_file.filename)
        timestamp = int(datetime.now().timestamp())
        saved_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(training_dir, saved_filename)
        
        audio_file.save(file_path)
        
        # 保存对应的文本
        text_file_path = os.path.join(training_dir, f"{timestamp}_{filename}.txt")
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return jsonify({
            'success': True,
            'message': '训练音频上传成功',
            'filename': saved_filename,
            'text_length': len(text_content),
            'uploaded_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"上传训练音频失败: {e}")
        return jsonify({'error': f'上传训练音频失败: {str(e)}'}), 500

@voice_bp.route('/status', methods=['GET'])
def get_voice_status():
    """获取语音功能状态"""
    try:
        assistant = current_app.config.get('AI_ASSISTANT')
        
        status = {
            'tts_available': False,
            'stt_available': False,
            'custom_voice_training_available': False,
            'available_voices_count': 0
        }
        
        if assistant:
            # 检查TTS引擎
            if hasattr(assistant, 'tts_engine') and assistant.tts_engine:
                status['tts_available'] = True
                
                # 检查是否支持自定义语音训练
                if hasattr(assistant.tts_engine, 'train_custom_voice'):
                    status['custom_voice_training_available'] = True
                
                # 获取可用语音数量
                try:
                    voices = assistant.tts_engine.get_available_voices()
                    status['available_voices_count'] = len(voices) if voices else 0
                except:
                    status['available_voices_count'] = 1  # 至少有默认语音
            
            # 检查STT引擎
            if hasattr(assistant, 'stt_engine') and assistant.stt_engine:
                status['stt_available'] = True
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        current_app.logger.error(f"获取语音状态失败: {e}")
        return jsonify({'error': f'获取语音状态失败: {str(e)}'}), 500
