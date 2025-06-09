"""
WebSocket事件处理器
提供实时通信功能，支持聊天、翻译、系统状态等实时更新
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask import current_app, request
import json
import time
from datetime import datetime
import threading

# 存储活跃连接
active_connections = {}
chat_rooms = {}

def register_socketio_handlers(socketio):
    """注册所有WebSocket事件处理器"""

    @socketio.on('connect')
    def handle_connect(auth):
        """客户端连接事件"""
        try:
            client_id = request.sid
            user_info = {
                'id': client_id,
                'connected_at': datetime.now().isoformat(),
                'ip': request.environ.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.environ.get('HTTP_USER_AGENT', 'unknown')
            }

            active_connections[client_id] = user_info

            current_app.logger.info(f"客户端连接: {client_id} from {user_info['ip']}")

            # 发送连接确认
            emit('connected', {
                'client_id': client_id,
                'server_time': datetime.now().isoformat(),
                'message': '连接成功'
            })

            # 发送系统状态
            emit('system_status', get_system_status())

        except Exception as e:
            current_app.logger.error(f"处理连接事件失败: {e}")
            emit('error', {'message': f'连接失败: {str(e)}'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接事件"""
        try:
            client_id = request.sid

            if client_id in active_connections:
                user_info = active_connections[client_id]
                del active_connections[client_id]

                current_app.logger.info(f"客户端断开连接: {client_id}")

            # 从所有房间中移除
            for room_id in list(chat_rooms.keys()):
                if client_id in chat_rooms[room_id]:
                    chat_rooms[room_id].remove(client_id)
                    if not chat_rooms[room_id]:  # 房间为空时删除
                        del chat_rooms[room_id]

        except Exception as e:
            current_app.logger.error(f"处理断开连接事件失败: {e}")

    @socketio.on('join_chat')
    def handle_join_chat(data):
        """加入聊天房间"""
        try:
            client_id = request.sid
            room_id = data.get('room_id', 'default')

            join_room(room_id)

            if room_id not in chat_rooms:
                chat_rooms[room_id] = []

            if client_id not in chat_rooms[room_id]:
                chat_rooms[room_id].append(client_id)

            emit('joined_chat', {
                'room_id': room_id,
                'message': f'已加入聊天房间: {room_id}'
            })

            current_app.logger.info(f"客户端 {client_id} 加入聊天房间: {room_id}")

        except Exception as e:
            current_app.logger.error(f"加入聊天房间失败: {e}")
            emit('error', {'message': f'加入聊天房间失败: {str(e)}'})

    @socketio.on('leave_chat')
    def handle_leave_chat(data):
        """离开聊天房间"""
        try:
            client_id = request.sid
            room_id = data.get('room_id', 'default')

            leave_room(room_id)

            if room_id in chat_rooms and client_id in chat_rooms[room_id]:
                chat_rooms[room_id].remove(client_id)
                if not chat_rooms[room_id]:
                    del chat_rooms[room_id]

            emit('left_chat', {
                'room_id': room_id,
                'message': f'已离开聊天房间: {room_id}'
            })

            current_app.logger.info(f"客户端 {client_id} 离开聊天房间: {room_id}")

        except Exception as e:
            current_app.logger.error(f"离开聊天房间失败: {e}")
            emit('error', {'message': f'离开聊天房间失败: {str(e)}'})

    @socketio.on('chat_message')
    def handle_chat_message(data):
        """处理聊天消息"""
        try:
            client_id = request.sid
            message = data.get('message', '').strip()
            room_id = data.get('room_id', 'default')
            knowledge_qa_enabled = data.get('knowledge_qa_enabled', True)  # 获取知识库问答开关状态
            selected_model = data.get('selected_model', 'local_default')  # 获取选择的模型

            if not message:
                emit('error', {'message': '消息内容不能为空'})
                return

            # 获取松瓷机电AI助手实例
            assistant = current_app.config.get('AI_ASSISTANT')
            if not assistant and selected_model == 'local_default':
                emit('error', {'message': '松瓷机电AI助手未初始化'})
                return

            # 发送用户消息到房间
            user_message = {
                'id': f"msg_{int(time.time() * 1000)}",
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat(),
                'client_id': client_id
            }

            socketio.emit('chat_message', user_message, room=room_id)

            # 发送"正在思考"状态
            thinking_message = {
                'id': f"thinking_{int(time.time() * 1000)}",
                'role': 'assistant',
                'content': '正在思考...',
                'timestamp': datetime.now().isoformat(),
                'type': 'thinking'
            }
            socketio.emit('chat_message', thinking_message, room=room_id)

            # 获取当前应用实例，用于线程中的应用上下文
            app = current_app._get_current_object()

            # 在后台线程中生成AI回复
            def generate_ai_response():
                # 在线程中需要应用上下文
                with app.app_context():
                    try:
                        # 确保应用WEB端严谨配置
                        web_config = app.config.get('AI_MODEL_CONFIG', {})
                        if web_config and hasattr(assistant, 'ai_engine'):
                            try:
                                if hasattr(assistant.ai_engine, 'chat_engine') and hasattr(assistant.ai_engine.chat_engine, 'generation_config'):
                                    generation_config = assistant.ai_engine.chat_engine.generation_config
                                    for key, value in web_config.items():
                                        if hasattr(generation_config, key):
                                            setattr(generation_config, key, value)
                                        elif isinstance(generation_config, dict):
                                            generation_config[key] = value
                            except Exception as e:
                                app.logger.warning(f'线程中应用配置失败: {e}')

                        # 导入所有需要的函数
                        from web_ui.api.chat_api import (_call_openai_model, _call_ollama_model,
                                                        _detect_ollama_models, _generate_knowledge_assisted_response,
                                                        _generate_external_model_knowledge_response,
                                                        _clean_ai_response, _manage_model_resources)

                        # 管理模型资源，在切换模型时优化GPU使用
                        _manage_model_resources(selected_model)

                        # 根据选择的模型类型调用不同的API
                        if selected_model.startswith('openai_'):
                            # OpenAI兼容API模型
                            model_name = selected_model.replace('openai_', '')
                            if knowledge_qa_enabled:
                                # 使用知识库辅助的OpenAI模型回答
                                ai_response = _generate_external_model_knowledge_response(assistant, message, model_name, 'openai')
                            else:
                                ai_response = _call_openai_model(model_name, message)
                        elif selected_model.startswith('ollama_') or selected_model in [model['id'] for model in _detect_ollama_models()]:
                            # Ollama模型
                            model_name = selected_model.replace('ollama_', '') if selected_model.startswith('ollama_') else selected_model
                            if knowledge_qa_enabled:
                                # 使用知识库辅助的Ollama模型回答
                                ai_response = _generate_external_model_knowledge_response(assistant, message, model_name, 'ollama')
                            else:
                                ai_response = _call_ollama_model(model_name, message, is_knowledge_query=False)
                        else:
                            # 本地模型（默认）
                            if knowledge_qa_enabled and hasattr(assistant, 'knowledge_base') and assistant.knowledge_base:
                                # 使用知识库问答模式 - 调用chat_api中的辅助函数
                                ai_response = _generate_knowledge_assisted_response(assistant, message)
                                ai_response = _clean_ai_response(ai_response)
                            else:
                                # 使用普通对话模式，添加markdown格式要求
                                markdown_prompt = (
                                    f"{message}\n\n"
                                    f"请使用Markdown格式回答，包括适当的标题、列表、代码块等格式。"
                                    f"保持回答的准确性和严谨性。"
                                )
                                ai_response = assistant.chat(markdown_prompt)

                        # 发送AI回复
                        ai_message = {
                            'id': f"ai_{int(time.time() * 1000)}",
                            'role': 'assistant',
                            'content': ai_response,
                            'timestamp': datetime.now().isoformat(),
                            'type': 'response',
                            'knowledge_qa_used': knowledge_qa_enabled,  # 标记是否使用了知识库问答
                            'model_used': selected_model  # 标记使用的模型
                        }

                        socketio.emit('chat_message', ai_message, room=room_id)

                        # 移除思考状态
                        socketio.emit('remove_thinking', {
                            'thinking_id': thinking_message['id']
                        }, room=room_id)

                    except Exception as e:
                        # 在应用上下文中记录错误
                        try:
                            app.logger.error(f"生成AI回复失败: {e}")
                        except:
                            print(f"生成AI回复失败: {e}")

                        error_message = {
                            'id': f"error_{int(time.time() * 1000)}",
                            'role': 'system',
                            'content': f'抱歉，处理您的请求时出现错误: {str(e)}',
                            'timestamp': datetime.now().isoformat(),
                            'type': 'error'
                        }
                        socketio.emit('chat_message', error_message, room=room_id)
                        socketio.emit('remove_thinking', {
                            'thinking_id': thinking_message['id']
                        }, room=room_id)

            # 启动后台线程
            thread = threading.Thread(target=generate_ai_response)
            thread.daemon = True
            thread.start()

        except Exception as e:
            current_app.logger.error(f"处理聊天消息失败: {e}")
            emit('error', {'message': f'处理聊天消息失败: {str(e)}'})

    @socketio.on('translation_request')
    def handle_translation_request(data):
        """处理翻译请求"""
        try:
            client_id = request.sid
            text = data.get('text', '').strip()
            source_lang = data.get('source_lang', 'auto')
            target_lang = data.get('target_lang', 'zh')

            if not text:
                emit('error', {'message': '翻译文本不能为空'})
                return

            # 获取松瓷机电AI助手实例
            assistant = current_app.config.get('AI_ASSISTANT')
            if not assistant or not hasattr(assistant, 'translator'):
                emit('error', {'message': '翻译引擎未初始化'})
                return

            # 发送翻译开始状态
            emit('translation_status', {
                'status': 'processing',
                'message': '正在翻译...'
            })

            # 获取当前应用实例，用于线程中的应用上下文
            app = current_app._get_current_object()

            # 在后台线程中执行翻译
            def perform_translation():
                with app.app_context():
                    try:
                        result = assistant.translator.translate(
                            text=text,
                            source_lang=source_lang,
                            target_lang=target_lang
                        )

                        # 发送翻译结果
                        socketio.emit('translation_result', {
                            'success': True,
                            'source_text': text,
                            'translated_text': result,
                            'source_lang': source_lang,
                            'target_lang': target_lang,
                            'timestamp': datetime.now().isoformat()
                        }, room=client_id)

                    except Exception as e:
                        app.logger.error(f"翻译失败: {e}")
                        socketio.emit('translation_result', {
                            'success': False,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }, room=client_id)

            # 启动后台线程
            thread = threading.Thread(target=perform_translation)
            thread.daemon = True
            thread.start()

        except Exception as e:
            current_app.logger.error(f"处理翻译请求失败: {e}")
            emit('error', {'message': f'处理翻译请求失败: {str(e)}'})

    @socketio.on('get_system_status')
    def handle_get_system_status():
        """获取系统状态"""
        try:
            status = get_system_status()
            emit('system_status', status)

        except Exception as e:
            current_app.logger.error(f"获取系统状态失败: {e}")
            emit('error', {'message': f'获取系统状态失败: {str(e)}'})

    @socketio.on('ping')
    def handle_ping():
        """处理心跳包"""
        emit('pong', {'timestamp': datetime.now().isoformat()})

def get_system_status():
    """获取系统状态信息"""
    try:
        assistant = current_app.config.get('AI_ASSISTANT')

        status = {
            'timestamp': datetime.now().isoformat(),
            'active_connections': len(active_connections),
            'chat_rooms': len(chat_rooms),
            'ai_assistant': {
                'available': assistant is not None,
                'components': {}
            }
        }

        if assistant:
            # 检查各个组件状态
            components = ['ai_engine', 'knowledge_base', 'vector_db', 'translator', 'term_base']
            for component in components:
                status['ai_assistant']['components'][component] = {
                    'available': hasattr(assistant, component) and getattr(assistant, component) is not None
                }

        return status

    except Exception as e:
        current_app.logger.error(f"获取系统状态失败: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }

def broadcast_system_update(update_type, data):
    """广播系统更新"""
    try:
        from flask import current_app
        # 检查是否在应用上下文中
        try:
            socketio = current_app.extensions.get('socketio')
            if socketio:
                socketio.emit('system_update', {
                    'type': update_type,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                })
        except RuntimeError:
            # 如果不在应用上下文中，则跳过广播
            print(f"无法广播系统更新 - 不在应用上下文中: {update_type}")
    except Exception as e:
        try:
            current_app.logger.error(f"广播系统更新失败: {e}")
        except:
            print(f"广播系统更新失败: {e}")
