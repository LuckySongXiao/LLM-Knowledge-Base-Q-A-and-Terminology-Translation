def __init__(self):
    """初始化设置"""
    self.config_path = 'config.json'
    self.config = {
        'language': 'zh',
        'model_path': '',
        'voice_model_path': '',
        'vector_model_path': '',
        'persona': '',
        'hyperparams': {
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 2048
        },
        'enable_multi_turn': False,  # 默认关闭多轮对话
        'max_context_turns': 5      # 多轮对话时的最大上下文轮数
    }
    
    # 加载保存的设置
    self.load() 

def get_ai_engine(self):
    """获取AI引擎"""
    if hasattr(self, 'ai_engine'):
        return self.ai_engine
    return None 