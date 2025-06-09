"""
缓存管理API
提供模型缓存状态查询和管理功能
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime

cache_bp = Blueprint('cache', __name__)

@cache_bp.route('/status', methods=['GET'])
def get_cache_status():
    """获取缓存状态"""
    try:
        from web_ui.model_cache import get_model_cache
        cache = get_model_cache()
        
        cache_info = cache.get_cache_info()
        
        # 获取松瓷机电AI助手状态
        assistant = current_app.config.get('AI_ASSISTANT')
        mock_mode = current_app.config.get('MOCK_MODE', False)
        
        status = {
            'cache_status': cache_info,
            'ai_assistant_available': assistant is not None,
            'mock_mode': mock_mode,
            'timestamp': datetime.now().isoformat()
        }
        
        if assistant and not mock_mode:
            # 获取模型信息
            try:
                model_info = {
                    'llm_loaded': hasattr(assistant, 'ai_engine') and assistant.ai_engine is not None,
                    'vector_loaded': hasattr(assistant, 'vector_db') and assistant.vector_db is not None,
                    'knowledge_base_items': len(assistant.knowledge_base.items) if hasattr(assistant, 'knowledge_base') and assistant.knowledge_base else 0,
                    'term_base_items': len(assistant.term_base.terms) if hasattr(assistant, 'term_base') and assistant.term_base else 0
                }
                status['model_info'] = model_info
            except Exception as e:
                status['model_info_error'] = str(e)
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        current_app.logger.error(f"获取缓存状态失败: {e}")
        return jsonify({'error': f'获取缓存状态失败: {str(e)}'}), 500

@cache_bp.route('/clear', methods=['POST'])
def clear_cache():
    """清除缓存"""
    try:
        from web_ui.model_cache import get_model_cache
        cache = get_model_cache()
        
        cache.clear_cache()
        
        # 清除应用配置中的松瓷机电AI助手
        current_app.config['AI_ASSISTANT'] = None
        current_app.config['MOCK_MODE'] = True
        
        return jsonify({
            'success': True,
            'message': '缓存已清除',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"清除缓存失败: {e}")
        return jsonify({'error': f'清除缓存失败: {str(e)}'}), 500

@cache_bp.route('/reload', methods=['POST'])
def reload_assistant():
    """重新加载松瓷机电AI助手"""
    try:
        from web_ui.model_cache import get_model_cache
        cache = get_model_cache()
        
        # 清除现有缓存
        cache.clear_cache()
        current_app.config['AI_ASSISTANT'] = None
        
        # 重新初始化
        from web_ui.app import initialize_ai_assistant
        success = initialize_ai_assistant(current_app)
        
        if success:
            return jsonify({
                'success': True,
                'message': '松瓷机电AI助手重新加载成功',
                'mock_mode': current_app.config.get('MOCK_MODE', False),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': '松瓷机电AI助手重新加载失败',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"重新加载松瓷机电AI助手失败: {e}")
        return jsonify({'error': f'重新加载松瓷机电AI助手失败: {str(e)}'}), 500
