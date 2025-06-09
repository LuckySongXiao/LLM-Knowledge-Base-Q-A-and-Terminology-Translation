"""
设置API模块
提供系统设置相关的RESTful API接口
"""

from flask import Blueprint, request, jsonify, current_app
import json
from datetime import datetime

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/config', methods=['GET'])
def get_config():
    """获取系统配置"""
    try:
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'settings'):
            return jsonify({'error': '设置模块未初始化'}), 500

        settings = assistant.settings

        # 获取所有配置（排除敏感信息）
        config_data = settings.get_all()

        # 过滤敏感配置
        sensitive_keys = ['secret_key', 'password', 'api_key', 'token']
        filtered_config = {}

        for key, value in config_data.items():
            if not any(sensitive in key.lower() for sensitive in sensitive_keys):
                filtered_config[key] = value

        return jsonify({
            'success': True,
            'config': filtered_config,
            'last_updated': datetime.now().isoformat()
        })

    except Exception as e:
        current_app.logger.error(f"获取配置失败: {e}")
        return jsonify({'error': f'获取配置失败: {str(e)}'}), 500

@settings_bp.route('/update', methods=['POST'])
def update_config():
    """更新系统配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'settings'):
            return jsonify({'error': '设置模块未初始化'}), 500

        settings = assistant.settings

        # 验证和更新配置
        updated_keys = []
        errors = []

        for key, value in data.items():
            try:
                # 验证配置项
                if key in ['temperature', 'top_p', 'top_k']:
                    # 验证数值范围
                    if not isinstance(value, (int, float)):
                        errors.append(f'{key} 必须是数字')
                        continue
                    if key == 'temperature' and not (0 <= value <= 2):
                        errors.append(f'temperature 必须在 0-2 之间')
                        continue
                    if key == 'top_p' and not (0 <= value <= 1):
                        errors.append(f'top_p 必须在 0-1 之间')
                        continue
                    if key == 'top_k' and not (1 <= value <= 100):
                        errors.append(f'top_k 必须在 1-100 之间')
                        continue

                elif key == 'max_new_tokens':
                    if not isinstance(value, int) or value < 1 or value > 4096:
                        errors.append(f'max_new_tokens 必须在 1-4096 之间')
                        continue

                elif key == 'language':
                    if value not in ['zh', 'en']:
                        errors.append(f'language 必须是 zh 或 en')
                        continue

                # 更新配置
                settings.set(key, value)
                updated_keys.append(key)

            except Exception as e:
                errors.append(f'更新 {key} 失败: {str(e)}')

        # 保存配置
        if updated_keys:
            try:
                settings.save()

                # 如果更新了AI引擎相关配置，重新加载
                ai_related_keys = [
                    'temperature', 'top_p', 'top_k', 'repetition_penalty', 'max_new_tokens',
                    'do_sample', 'model_path', 'kb_top_k', 'kb_threshold', 'kb_temperature',
                    'enable_knowledge'
                ]
                if any(key in ai_related_keys for key in updated_keys):
                    if hasattr(assistant, 'ai_engine'):
                        assistant.ai_engine.update_settings(settings.get_all())
                        current_app.logger.info(f'已更新AI引擎配置: {[k for k in updated_keys if k in ai_related_keys]}')

            except Exception as e:
                errors.append(f'保存配置失败: {str(e)}')

        if errors:
            return jsonify({
                'success': False,
                'errors': errors,
                'updated_keys': updated_keys
            }), 400

        return jsonify({
            'success': True,
            'message': f'成功更新 {len(updated_keys)} 个配置项',
            'updated_keys': updated_keys
        })

    except Exception as e:
        current_app.logger.error(f"更新配置失败: {e}")
        return jsonify({'error': f'更新配置失败: {str(e)}'}), 500

@settings_bp.route('/models', methods=['GET'])
def get_models():
    """获取可用模型列表"""
    try:
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant:
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500

        models_info = {
            'llm_models': [],
            'embedding_models': [],
            'current_llm': None,
            'current_embedding': None
        }

        # 获取模型管理器
        if hasattr(assistant, 'model_manager') and assistant.model_manager:
            model_manager = assistant.model_manager

            # 获取LLM模型
            try:
                llm_path = model_manager.get_model_path(model_manager.MODEL_TYPE_LLM)
                llm_models = model_manager.detect_models(llm_path, model_manager.MODEL_TYPE_LLM)
                models_info['llm_models'] = [
                    {
                        'name': model['name'],
                        'path': model['path'],
                        'size': model.get('size', 'Unknown'),
                        'type': 'LLM'
                    }
                    for model in llm_models
                ]
            except Exception as e:
                current_app.logger.warning(f"获取LLM模型列表失败: {e}")

            # 获取向量模型
            try:
                embedding_path = model_manager.get_model_path(model_manager.MODEL_TYPE_EMBEDDING)
                embedding_models = model_manager.detect_models(embedding_path, model_manager.MODEL_TYPE_EMBEDDING)
                models_info['embedding_models'] = [
                    {
                        'name': model['name'],
                        'path': model['path'],
                        'size': model.get('size', 'Unknown'),
                        'type': 'Embedding'
                    }
                    for model in embedding_models
                ]
            except Exception as e:
                current_app.logger.warning(f"获取向量模型列表失败: {e}")

        # 获取当前使用的模型状态
        try:
            # 检查LLM模型状态
            llm_status = _check_llm_model_status(assistant)
            models_info['current_llm'] = llm_status
        except Exception as e:
            current_app.logger.warning(f"获取当前LLM模型信息失败: {e}")
            models_info['current_llm'] = {
                'name': 'Unknown',
                'status': 'error',
                'error': str(e)
            }

        try:
            # 检查向量模型状态
            embedding_status = _check_embedding_model_status(assistant)
            models_info['current_embedding'] = embedding_status
        except Exception as e:
            current_app.logger.warning(f"获取当前向量模型信息失败: {e}")
            models_info['current_embedding'] = {
                'name': 'Unknown',
                'status': 'error',
                'error': str(e)
            }

        return jsonify({
            'success': True,
            'models': models_info
        })

    except Exception as e:
        current_app.logger.error(f"获取模型列表失败: {e}")
        return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

@settings_bp.route('/system_info', methods=['GET'])
def get_system_info():
    """获取系统信息"""
    try:
        import psutil
        import platform
        import torch

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')

        system_info = {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used
            },
            'cpu': {
                'count': psutil.cpu_count(),
                'percent': psutil.cpu_percent(interval=1)
            },
            'gpu': {
                'available': torch.cuda.is_available(),
                'count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
                'devices': []
            },
            'ai_assistant': {
                'initialized': assistant is not None,
                'components': {}
            }
        }

        # GPU信息
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                gpu_info = {
                    'id': i,
                    'name': torch.cuda.get_device_name(i),
                    'memory_total': torch.cuda.get_device_properties(i).total_memory,
                    'memory_allocated': torch.cuda.memory_allocated(i),
                    'memory_reserved': torch.cuda.memory_reserved(i)
                }
                system_info['gpu']['devices'].append(gpu_info)

        # 松瓷机电AI助手组件状态
        if assistant:
            components = ['ai_engine', 'knowledge_base', 'vector_db', 'translator', 'term_base']
            for component in components:
                system_info['ai_assistant']['components'][component] = hasattr(assistant, component) and getattr(assistant, component) is not None

        return jsonify({
            'success': True,
            'system_info': system_info
        })

    except Exception as e:
        current_app.logger.error(f"获取系统信息失败: {e}")
        return jsonify({'error': f'获取系统信息失败: {str(e)}'}), 500

def _check_llm_model_status(assistant):
    """检查LLM模型状态"""
    try:
        # 检查AI引擎
        if not hasattr(assistant, 'ai_engine') or not assistant.ai_engine:
            return {
                'name': 'LLM模型',
                'status': 'not_initialized',
                'message': 'AI引擎未初始化',
                'device': 'N/A',
                'memory_usage': 'N/A',
                'model_path': 'N/A'
            }

        ai_engine = assistant.ai_engine

        # 检查聊天引擎
        if hasattr(ai_engine, 'chat_engine') and ai_engine.chat_engine:
            chat_engine = ai_engine.chat_engine

            # 检查模型是否加载
            if hasattr(chat_engine, 'model') and chat_engine.model:
                # 尝试获取模型信息
                model_info = {
                    'name': getattr(chat_engine, 'model_type', 'Unknown LLM'),
                    'status': 'loaded',
                    'device': getattr(chat_engine, 'device', 'Unknown'),
                    'model_path': getattr(chat_engine, 'model_path', 'Unknown'),
                    'memory_usage': _get_gpu_memory_usage()
                }

                # 测试模型是否可用
                try:
                    # 简单的模型测试
                    test_result = chat_engine.generate("测试", max_new_tokens=1)
                    if test_result:
                        model_info['status'] = 'active'
                        model_info['message'] = '模型运行正常'
                    else:
                        model_info['status'] = 'loaded_but_inactive'
                        model_info['message'] = '模型已加载但响应异常'
                except Exception as e:
                    model_info['status'] = 'loaded_but_error'
                    model_info['message'] = f'模型测试失败: {str(e)}'

                return model_info
            else:
                return {
                    'name': 'LLM模型',
                    'status': 'not_loaded',
                    'message': '模型未加载',
                    'device': 'N/A',
                    'memory_usage': 'N/A',
                    'model_path': 'N/A'
                }
        else:
            return {
                'name': 'LLM模型',
                'status': 'engine_not_ready',
                'message': '聊天引擎未就绪',
                'device': 'N/A',
                'memory_usage': 'N/A',
                'model_path': 'N/A'
            }

    except Exception as e:
        return {
            'name': 'LLM模型',
            'status': 'error',
            'message': f'状态检查失败: {str(e)}',
            'device': 'N/A',
            'memory_usage': 'N/A',
            'model_path': 'N/A'
        }

def _check_embedding_model_status(assistant):
    """检查向量模型状态"""
    try:
        # 检查知识库
        if not hasattr(assistant, 'knowledge_base') or not assistant.knowledge_base:
            return {
                'name': '向量模型',
                'status': 'not_initialized',
                'message': '知识库未初始化',
                'device': 'N/A',
                'model_path': 'N/A'
            }

        knowledge_base = assistant.knowledge_base

        # 检查向量模型
        if hasattr(knowledge_base, 'vector_model') and knowledge_base.vector_model:
            model_info = {
                'name': 'BGE-M3',
                'status': 'loaded',
                'device': 'CPU',
                'model_path': getattr(knowledge_base, 'vector_model_path', 'Unknown')
            }

            # 测试向量模型
            try:
                # 简单的向量编码测试
                test_vector = knowledge_base.vector_model.encode("测试文本")
                if test_vector is not None and len(test_vector) > 0:
                    model_info['status'] = 'active'
                    model_info['message'] = '向量模型运行正常'
                    model_info['vector_dim'] = len(test_vector)
                else:
                    model_info['status'] = 'loaded_but_inactive'
                    model_info['message'] = '向量模型响应异常'
            except Exception as e:
                model_info['status'] = 'loaded_but_error'
                model_info['message'] = f'向量模型测试失败: {str(e)}'

            return model_info
        else:
            return {
                'name': '向量模型',
                'status': 'not_loaded',
                'message': '向量模型未加载',
                'device': 'N/A',
                'model_path': 'N/A'
            }

    except Exception as e:
        return {
            'name': '向量模型',
            'status': 'error',
            'message': f'状态检查失败: {str(e)}',
            'device': 'N/A',
            'model_path': 'N/A'
        }

def _get_gpu_memory_usage():
    """获取GPU内存使用情况"""
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0)
            reserved = torch.cuda.memory_reserved(0)
            total = torch.cuda.get_device_properties(0).total_memory

            return {
                'allocated_gb': allocated / (1024**3),
                'reserved_gb': reserved / (1024**3),
                'total_gb': total / (1024**3),
                'usage_percent': (allocated / total) * 100
            }
        else:
            return 'CUDA不可用'
    except Exception as e:
        return f'获取失败: {str(e)}'
