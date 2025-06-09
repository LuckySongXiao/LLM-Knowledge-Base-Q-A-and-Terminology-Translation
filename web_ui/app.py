"""
松瓷机电AI助手WEB UI主应用
基于Flask和Socket.IO的WEB界面，提供与PC端UI相同的功能
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO
from flask_cors import CORS

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 确保可以找到 config 模块
config_path = os.path.join(project_root, 'config')
if config_path not in sys.path:
    sys.path.insert(0, config_path)

# 导入配置和模块
from web_ui.config.web_config import get_config
from web_ui.api import register_api_blueprints
from web_ui.websocket.handlers import register_socketio_handlers

def create_app(config_name=None):
    """创建Flask应用实例"""
    app = Flask(__name__)

    # 加载配置
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # 初始化配置
    config_class.init_app(app)

    # 配置CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    # 配置日志
    setup_logging(app)

    # 初始化Socket.IO
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*'),
        async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading')
    )

    # 注册API蓝图
    register_api_blueprints(app)

    # 注册WebSocket事件处理器
    register_socketio_handlers(socketio)

    # 注册路由
    register_routes(app)

    # 注册错误处理器
    register_error_handlers(app)

    return app, socketio

def setup_logging(app):
    """配置日志系统"""
    if not app.debug and not app.testing:
        # 创建日志目录
        log_dir = os.path.dirname(app.config.get('LOG_FILE', 'logs/web_ui.log'))
        os.makedirs(log_dir, exist_ok=True)

        # 配置文件日志处理器
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'logs/web_ui.log'),
            maxBytes=app.config.get('LOG_MAX_SIZE', 10 * 1024 * 1024),
            backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
        )

        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))

        file_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.addHandler(file_handler)

        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.info('松瓷机电AI助手WEB UI启动')

def register_routes(app):
    """注册路由"""

    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')

    @app.route('/chat')
    def chat():
        """聊天页面"""
        return render_template('chat.html')

    @app.route('/translation')
    def translation():
        """翻译页面"""
        return render_template('translation.html')

    @app.route('/knowledge')
    def knowledge():
        """知识库页面"""
        return render_template('knowledge.html')

    @app.route('/settings')
    def settings():
        """设置页面"""
        return render_template('settings.html')

    @app.route('/voice')
    def voice():
        """语音页面"""
        return render_template('voice.html')

    @app.route('/terminology')
    def terminology():
        """术语库页面"""
        return render_template('terminology.html')

    @app.route('/health')
    def health_check():
        """健康检查接口"""
        try:
            assistant = app.config.get('AI_ASSISTANT')
            status = {
                'status': 'healthy',
                'timestamp': '2024-01-01T00:00:00',
                'ai_assistant_available': assistant is not None,
                'version': '1.0.0'
            }
            return jsonify(status)
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': '2024-01-01T00:00:00'
            }), 500

def register_error_handlers(app):
    """注册错误处理器"""

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': '接口不存在'}), 404
        return render_template('error.html', error_code=404, error_message='页面不存在'), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': '服务器内部错误'}), 500
        return render_template('error.html', error_code=500, error_message='服务器内部错误'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': '访问被拒绝'}), 403
        return render_template('error.html', error_code=403, error_message='访问被拒绝'), 403

def initialize_ai_assistant(app):
    """初始化松瓷机电AI助手实例（使用缓存机制避免重复加载）"""
    try:
        # 导入模型缓存
        from web_ui.model_cache import get_model_cache
        cache = get_model_cache()

        # 检查是否已有缓存的实例
        if cache.is_cached():
            cached_assistant = cache.get_ai_assistant()
            if cached_assistant:
                app.config['AI_ASSISTANT'] = cached_assistant
                app.config['MOCK_MODE'] = False
                cache_info = cache.get_cache_info()
                app.logger.info(f'使用缓存的松瓷机电AI助手实例 (缓存时间: {cache_info["load_time"]}, 缓存年龄: {cache_info["cache_age_seconds"]:.1f}秒)')
                return True

        # 检查是否正在加载中
        if cache.is_currently_loading():
            app.logger.info('松瓷机电AI助手正在其他进程中加载，等待完成...')
            # 等待加载完成，最多等待60秒
            for i in range(60):
                time.sleep(1)
                if cache.is_cached():
                    cached_assistant = cache.get_ai_assistant()
                    if cached_assistant:
                        app.config['AI_ASSISTANT'] = cached_assistant
                        app.config['MOCK_MODE'] = False
                        app.logger.info('松瓷机电AI助手加载完成，使用缓存实例')
                        return True

            app.logger.warning('等待松瓷机电AI助手加载超时，切换到模拟模式')

        # 设置加载状态
        cache.set_loading_status(True)
        app.logger.info('正在初始化松瓷机电AI助手...')

        # 尝试导入松瓷机电AI助手类
        try:
            from AI_assistant import AIAssistant
        except ImportError as e:
            cache.set_loading_status(False)
            app.logger.warning(f'无法导入松瓷机电AI助手模块: {e}')
            app.logger.info('WEB UI将以模拟模式运行，使用模拟松瓷机电AI助手')

            # 使用模拟松瓷机电AI助手
            from web_ui.mock_assistant import MockAIAssistant
            mock_assistant = MockAIAssistant()
            app.config['AI_ASSISTANT'] = mock_assistant
            app.config['MOCK_MODE'] = True
            return True

        # 尝试创建松瓷机电AI助手实例
        try:
            assistant = AIAssistant(web_mode=True)  # 明确指定为web模式

            # 应用WEB端严谨配置
            web_config = app.config.get('AI_MODEL_CONFIG', {})
            if web_config and hasattr(assistant, 'ai_engine'):
                try:
                    # 更新聊天引擎配置
                    if hasattr(assistant.ai_engine, 'chat_engine'):
                        chat_engine = assistant.ai_engine.chat_engine
                        if hasattr(chat_engine, 'generation_config'):
                            # 直接设置属性而不是使用update方法
                            for key, value in web_config.items():
                                if hasattr(chat_engine.generation_config, key):
                                    setattr(chat_engine.generation_config, key, value)
                                elif isinstance(chat_engine.generation_config, dict):
                                    chat_engine.generation_config[key] = value
                            app.logger.info(f'已应用WEB端严谨配置: temperature={web_config.get("temperature", 0.3)}')

                    # 更新知识库引擎配置
                    if hasattr(assistant.ai_engine, 'knowledge_engine'):
                        knowledge_engine = assistant.ai_engine.knowledge_engine
                        if hasattr(knowledge_engine, 'generation_config'):
                            # 直接设置属性而不是使用update方法
                            for key, value in web_config.items():
                                if hasattr(knowledge_engine.generation_config, key):
                                    setattr(knowledge_engine.generation_config, key, value)
                                elif isinstance(knowledge_engine.generation_config, dict):
                                    knowledge_engine.generation_config[key] = value
                            app.logger.info('已应用知识库引擎严谨配置')
                except Exception as e:
                    app.logger.warning(f'应用WEB端配置失败: {e}')

            # 缓存实例
            cache.set_ai_assistant(assistant)

            app.config['AI_ASSISTANT'] = assistant
            app.config['MOCK_MODE'] = False
            app.logger.info('松瓷机电AI助手初始化成功并已缓存')
            return True

        except Exception as e:
            cache.set_loading_status(False)
            app.logger.warning(f'松瓷机电AI助手实例化失败: {e}')
            app.logger.info('WEB UI将以模拟模式运行，使用模拟松瓷机电AI助手')

            # 使用模拟松瓷机电AI助手
            from web_ui.mock_assistant import MockAIAssistant
            mock_assistant = MockAIAssistant()
            app.config['AI_ASSISTANT'] = mock_assistant
            app.config['MOCK_MODE'] = True
            return True

    except Exception as e:
        # 确保清除加载状态
        try:
            from web_ui.model_cache import get_model_cache
            get_model_cache().set_loading_status(False)
        except:
            pass

        app.logger.error(f'松瓷机电AI助手初始化过程中发生未知错误: {e}')
        app.logger.info('WEB UI将以模拟模式运行，使用模拟松瓷机电AI助手')

        # 使用模拟松瓷机电AI助手作为后备
        try:
            from web_ui.mock_assistant import MockAIAssistant
            mock_assistant = MockAIAssistant()
            app.config['AI_ASSISTANT'] = mock_assistant
            app.config['MOCK_MODE'] = True
            return True
        except Exception as mock_error:
            app.logger.error(f'模拟松瓷机电AI助手初始化也失败: {mock_error}')
            app.config['AI_ASSISTANT'] = None
            return False

def main():
    """主函数"""
    # 确保工作目录是项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # 上一级目录

    print(f"当前脚本目录: {current_dir}")
    print(f"项目根目录: {project_root}")
    print(f"切换前工作目录: {os.getcwd()}")

    # 切换到项目根目录
    os.chdir(project_root)
    print(f"切换后工作目录: {os.getcwd()}")

    # 验证数据目录是否存在
    data_dir = os.path.join(project_root, 'data')
    if os.path.exists(data_dir):
        print(f"✓ 数据目录存在: {data_dir}")
        # 列出数据目录内容
        try:
            contents = os.listdir(data_dir)
            print(f"数据目录内容: {contents}")
        except Exception as e:
            print(f"无法列出数据目录内容: {e}")
    else:
        print(f"✗ 数据目录不存在: {data_dir}")

    # 设置环境变量
    os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # 获取配置名称
    config_name = os.environ.get('FLASK_ENV', 'development')

    # 创建应用
    app, socketio = create_app(config_name)

    # 初始化松瓷机电AI助手
    ai_initialized = initialize_ai_assistant(app)
    if not ai_initialized:
        print("注意: 松瓷机电AI助手未初始化，某些功能可能不可用")
    elif app.config.get('MOCK_MODE', False):
        print("注意: 使用模拟松瓷机电AI助手，功能仅供演示")

    # 获取配置
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', False)

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    松瓷机电AI助手 WEB UI 服务                 ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  本地访问: http://localhost:{port}                            ║
    ║  局域网访问: http://{host}:{port}                             ║
    ║  配置环境: {config_name}                                      ║
    ║  调试模式: {'开启' if debug else '关闭'}                                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        # 启动服务器
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,  # 禁用自动重启，避免模型重复加载
            allow_unsafe_werkzeug=True  # 允许在生产环境中使用Werkzeug
        )
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
