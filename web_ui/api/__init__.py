"""
API模块初始化文件
包含所有API蓝图的注册
"""

from flask import Blueprint

def register_api_blueprints(app):
    """注册所有API蓝图"""
    from .chat_api import chat_bp
    from .translation_api import translation_bp
    from .knowledge_api import knowledge_bp
    from .settings_api import settings_bp
    from .voice_api import voice_bp
    from .terminology_api import terminology_bp
    from .cache_api import cache_bp

    # 注册API蓝图
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(translation_bp, url_prefix='/api/translation')
    app.register_blueprint(knowledge_bp, url_prefix='/api/knowledge')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(voice_bp, url_prefix='/api/voice')
    app.register_blueprint(terminology_bp, url_prefix='/api/terminology')
    app.register_blueprint(cache_bp, url_prefix='/api/cache')
