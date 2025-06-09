"""
模拟松瓷机电AI助手类
当真实的松瓷机电AI助手无法初始化时，提供基本的模拟功能
"""

import time
from datetime import datetime

class MockAIAssistant:
    """模拟松瓷机电AI助手类，提供基本的模拟功能"""
    
    def __init__(self):
        self.name = "模拟松瓷机电AI助手"
        self.version = "1.0.0"
        self.initialized = True
        
        # 模拟组件
        self.ai_engine = MockAIEngine()
        self.translator = MockTranslator()
        self.knowledge_base = MockKnowledgeBase()
        self.vector_db = MockVectorDB()
        self.term_base = MockTermBase()
        self.tts_engine = MockTTSEngine()
        self.stt_engine = MockSTTEngine()
        self.settings = MockSettings()
        self.model_manager = MockModelManager()
    
    def chat(self, message, history=None):
        """模拟聊天功能"""
        # 简单的模拟回复
        responses = [
            f"您好！您说的是：{message}",
            f"这是一个模拟回复。您的消息是：{message}",
            f"抱歉，我是模拟松瓷机电AI助手，无法提供真实的AI回复。您的输入：{message}",
            f"模拟模式下，我收到了您的消息：{message}",
            f"感谢您的输入：{message}。这是一个测试回复。"
        ]
        
        # 模拟思考时间
        time.sleep(1)
        
        # 根据消息内容选择回复
        message_lower = message.lower()
        if "你好" in message_lower or "hello" in message_lower:
            return "您好！我是模拟松瓷机电AI助手，很高兴为您服务！"
        elif "翻译" in message_lower:
            return "翻译功能需要真实的松瓷机电AI助手支持。当前为模拟模式。"
        elif "知识" in message_lower:
            return "知识库功能需要真实的松瓷机电AI助手支持。当前为模拟模式。"
        else:
            import random
            return random.choice(responses)

class MockAIEngine:
    """模拟AI引擎"""
    
    def __init__(self):
        self.chat_engine = MockChatEngine()
    
    def update_settings(self, settings):
        """更新设置"""
        pass

class MockChatEngine:
    """模拟聊天引擎"""
    
    def __init__(self):
        self.model = {
            'name': '模拟模型',
            'type': 'Mock',
            'device': 'CPU',
            'path': '/mock/model/path'
        }

class MockTranslator:
    """模拟翻译器"""
    
    def translate(self, text, source_lang='auto', target_lang='zh'):
        """模拟翻译功能"""
        time.sleep(0.5)  # 模拟翻译时间
        
        # 简单的模拟翻译
        if source_lang == 'zh' and target_lang == 'en':
            return f"[Mock Translation to English]: {text}"
        elif source_lang == 'en' and target_lang == 'zh':
            return f"[模拟翻译为中文]: {text}"
        else:
            return f"[模拟翻译 {source_lang}->{target_lang}]: {text}"

class MockKnowledgeBase:
    """模拟知识库"""
    
    def __init__(self):
        self.mock_items = [
            {
                'id': 'mock_1',
                'title': '模拟知识条目1',
                'content': '这是一个模拟的知识条目内容。',
                'type': 'text',
                'tags': ['模拟', '测试'],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 'mock_2',
                'title': '模拟知识条目2',
                'content': '这是另一个模拟的知识条目内容。',
                'type': 'text',
                'tags': ['示例', '演示'],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
        self.vector_db = MockVectorDB()
    
    def list_items(self):
        """获取知识条目列表"""
        return self.mock_items
    
    def get_item(self, item_id):
        """获取指定知识条目"""
        for item in self.mock_items:
            if item['id'] == item_id:
                return item
        return None
    
    def add_item(self, title, data):
        """添加知识条目"""
        new_item = {
            'id': f'mock_{len(self.mock_items) + 1}',
            'title': title,
            'content': data.get('content', ''),
            'type': data.get('type', 'text'),
            'tags': data.get('tags', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.mock_items.append(new_item)
        return True
    
    def update_item(self, item_id, data):
        """更新知识条目"""
        for i, item in enumerate(self.mock_items):
            if item['id'] == item_id:
                self.mock_items[i].update(data)
                self.mock_items[i]['updated_at'] = datetime.now().isoformat()
                return True
        return False
    
    def delete_item(self, item_id):
        """删除知识条目"""
        for i, item in enumerate(self.mock_items):
            if item['id'] == item_id:
                del self.mock_items[i]
                return True
        return False
    
    def search(self, query, limit=10, threshold=0.7):
        """搜索知识条目"""
        results = []
        query_lower = query.lower()
        
        for item in self.mock_items:
            if (query_lower in item['title'].lower() or 
                query_lower in item['content'].lower()):
                results.append({
                    **item,
                    'score': 0.9  # 模拟相似度分数
                })
        
        return results[:limit]
    
    def import_file(self, file_path):
        """导入文件"""
        # 模拟文件导入
        import os
        filename = os.path.basename(file_path)
        
        new_item = {
            'id': f'mock_file_{len(self.mock_items) + 1}',
            'title': f'导入的文件: {filename}',
            'content': f'这是从文件 {filename} 导入的模拟内容。',
            'type': 'file',
            'tags': ['导入', '文件'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.mock_items.append(new_item)
        return True

class MockVectorDB:
    """模拟向量数据库"""
    
    def __init__(self):
        self.model = {
            'name': '模拟向量模型',
            'device': 'CPU',
            'path': '/mock/vector/model'
        }

class MockTermBase:
    """模拟术语库"""
    pass

class MockTTSEngine:
    """模拟TTS引擎"""
    
    def synthesize_to_file(self, text, output_path, voice='default', speed=1.0, pitch=1.0):
        """模拟语音合成"""
        # 创建一个空的音频文件（实际应用中这里会生成真实的音频）
        with open(output_path, 'wb') as f:
            f.write(b'MOCK_AUDIO_DATA')  # 模拟音频数据
        return True
    
    def get_available_voices(self):
        """获取可用语音列表"""
        return [
            {'id': 'default', 'name': '默认语音', 'language': 'zh', 'gender': 'female'},
            {'id': 'male', 'name': '男声', 'language': 'zh', 'gender': 'male'},
            {'id': 'female', 'name': '女声', 'language': 'zh', 'gender': 'female'}
        ]

class MockSTTEngine:
    """模拟STT引擎"""
    
    def transcribe(self, audio_path):
        """模拟语音识别"""
        time.sleep(1)  # 模拟处理时间
        return "这是模拟的语音识别结果。"

class MockSettings:
    """模拟设置管理"""
    
    def __init__(self):
        self.settings = {
            'temperature': 0.7,
            'top_p': 0.9,
            'top_k': 50,
            'max_new_tokens': 512,
            'language': 'zh',
            'system_prompt': '你是一个有用的松瓷机电AI助手。'
        }
    
    def get_all(self):
        """获取所有设置"""
        return self.settings.copy()
    
    def get(self, key, default=None):
        """获取指定设置"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """设置指定值"""
        self.settings[key] = value
    
    def save(self):
        """保存设置"""
        pass  # 模拟保存

class MockModelManager:
    """模拟模型管理器"""
    
    MODEL_TYPE_LLM = 'llm'
    MODEL_TYPE_EMBEDDING = 'embedding'
    
    def get_model_path(self, model_type):
        """获取模型路径"""
        return f'/mock/models/{model_type}'
    
    def detect_models(self, path, model_type):
        """检测可用模型"""
        if model_type == self.MODEL_TYPE_LLM:
            return [
                {'name': '模拟LLM模型1', 'path': '/mock/llm1', 'size': '7B'},
                {'name': '模拟LLM模型2', 'path': '/mock/llm2', 'size': '13B'}
            ]
        elif model_type == self.MODEL_TYPE_EMBEDDING:
            return [
                {'name': '模拟向量模型1', 'path': '/mock/embed1', 'size': '400M'},
                {'name': '模拟向量模型2', 'path': '/mock/embed2', 'size': '800M'}
            ]
        return []
