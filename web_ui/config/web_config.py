"""
WEB UI配置文件
包含Flask应用的所有配置参数
"""

import os
import secrets

class Config:
    """基础配置类"""

    # 服务器配置
    HOST = '0.0.0.0'  # 监听所有网络接口，支持局域网访问
    PORT = 5000       # 服务端口
    DEBUG = False     # 生产环境关闭调试模式

    # 安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # 会话配置
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'ai_assistant:'

    # CORS配置
    CORS_ORIGINS = ['*']  # 允许所有来源，生产环境应限制

    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'md'}

    # WebSocket配置
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'

    # 用户认证配置
    ENABLE_AUTH = False  # 默认关闭认证，可根据需要开启
    DEFAULT_USERNAME = 'admin'
    DEFAULT_PASSWORD = 'admin123'

    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/web_ui.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # API配置
    API_PREFIX = '/api'
    API_VERSION = 'v1'

    # 静态文件配置
    STATIC_FOLDER = 'static'
    TEMPLATE_FOLDER = 'templates'

    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟

    # AI模型配置 - WEB端专用严谨设置
    AI_MODEL_CONFIG = {
        'temperature': 0.3,          # 降低温度提高严谨度
        'top_p': 0.6,               # 降低top_p减少随机性
        'top_k': 15,                # 限制候选词数量
        'repetition_penalty': 1.2,   # 增加重复惩罚
        'max_new_tokens': 2048,     # 最大生成长度
        'do_sample': True           # 启用采样但参数保守
    }

    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        os.makedirs('logs', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    HOST = '127.0.0.1'  # 开发环境只监听本地
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    HOST = '0.0.0.0'    # 生产环境监听所有接口
    ENABLE_AUTH = False  # 暂时禁用认证，便于测试
    CORS_ORIGINS = ['*']   # 允许所有来源，便于局域网访问

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    HOST = '127.0.0.1'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """获取配置类"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    return config.get(config_name, config['default'])
