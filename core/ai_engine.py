import os
import logging
import torch
from .base_engine import BaseEngine
from .chat_engine import ChatEngine
from .knowledge_engine import KnowledgeEngine
from .translation_engine import TranslationEngine

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIEngine:
    """AI模型引擎包装器，根据任务类型调用相应的专用引擎"""
    
    def __init__(self, settings):
        """初始化AI引擎包装器"""
        self.settings = settings
        
        # 初始化各个专用引擎
        self.chat_engine = ChatEngine(settings)
        self.knowledge_engine = KnowledgeEngine(settings)
        self.translation_engine = TranslationEngine(settings)
        
        logger.info(f"初始化AI引擎包装器完成")
        
        # 术语库和知识库将由外部设置
        self.terms = {}
    
    def load_models(self):
        """加载所有引擎的模型"""
        # 修改为只加载一次模型
        if self.chat_engine.model is None:
            logger.info("开始加载模型...")
            success = self.chat_engine.load_models()
            if success and self.chat_engine.model is not None:
                # 模型加载成功，共享给其他引擎
                logger.info("模型加载成功，共享给其他引擎")
                self.knowledge_engine.model = self.chat_engine.model
                self.knowledge_engine.tokenizer = self.chat_engine.tokenizer
                self.knowledge_engine.model_path = self.chat_engine.model_path
                
                self.translation_engine.model = self.chat_engine.model
                self.translation_engine.tokenizer = self.chat_engine.tokenizer
                self.translation_engine.model_path = self.chat_engine.model_path
                return True
            else:
                logger.error("模型加载失败")
                return False
        else:
            logger.info("模型已加载，无需重复加载")
            return True
    
    def generate_response(self, messages, is_knowledge_query=False, knowledge=None):
        """根据提供的消息生成回复，自动判断使用哪个引擎"""
        try:
            # 检查消息内容，判断是否为翻译任务
            is_translation_task = False
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and ("translate" in content.lower() or "翻译" in content):
                    is_translation_task = True
                    break
            
            # 根据任务类型选择合适的引擎
            if is_translation_task:
                logger.info("检测到翻译任务，使用翻译引擎")
                return self.translation_engine.generate_response(messages)
            elif is_knowledge_query and knowledge:
                logger.info("检测到知识库查询，使用知识库引擎")
                return self.knowledge_engine.generate_response(messages, knowledge)
            else:
                logger.info("使用聊天引擎生成回复")
                return self.chat_engine.generate_response(messages)
                
        except Exception as e:
            import traceback
            logger.error(f"生成回复时出错: {e}")
            traceback.print_exc()
            return f"生成回复时出错: {str(e)}"
    
    def translate_text(self, text, source_lang=None, target_lang='en', use_termbase=True):
        """翻译文本，转发到翻译引擎"""
        return self.translation_engine.translate_text(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            use_termbase=use_termbase
        )
    
    def translate(self, text, source_lang=None, target_lang='en', use_termbase=True):
        """翻译文本的简便方法，转发到翻译引擎"""
        return self.translation_engine.translate(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            use_termbase=use_termbase
        )
    
    def get_vector_embedding(self, text):
        """获取文本的向量嵌入"""
        # 默认使用知识库引擎的向量嵌入功能
        if hasattr(self.knowledge_engine, 'get_vector_embedding'):
            return self.knowledge_engine.get_vector_embedding(text)
        return None
    
    def update_settings(self, new_settings):
        """更新所有引擎的设置"""
        # 更新各引擎的设置
        self.chat_engine.update_settings(new_settings)
        self.knowledge_engine.update_settings(new_settings)
        self.translation_engine.update_settings(new_settings)
        
        # 更新自身设置
        self.settings = new_settings

    def set_model(self, model_info):
        """设置所有引擎的模型"""
        try:
            model_path = model_info.get('path', '')
            model_name = model_info.get('name', os.path.basename(model_path))
            model_type = model_info.get('type', 'safetensors')
            
            logger.info(f"设置模型: {model_name}, 路径: {model_path}, 类型: {model_type}")
            
            # 只在chat_engine中加载模型
            success = self.chat_engine.set_model(model_info)
            if success and self.chat_engine.model is not None:
                # 模型加载成功，共享给其他引擎
                logger.info("成功加载模型，现在共享给其他引擎")
                
                # 共享模型和tokenizer到其他引擎
                self.knowledge_engine.model = self.chat_engine.model
                self.knowledge_engine.tokenizer = self.chat_engine.tokenizer
                self.knowledge_engine.model_path = self.chat_engine.model_path
                
                self.translation_engine.model = self.chat_engine.model
                self.translation_engine.tokenizer = self.chat_engine.tokenizer
                self.translation_engine.model_path = self.chat_engine.model_path
                
                return True
            else:
                logger.error("模型加载失败")
                return False
        except Exception as e:
            logger.error(f"设置模型失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_knowledge_base(self, knowledge_base):
        """设置知识库"""
        self.knowledge_engine.set_knowledge_base(knowledge_base)
    
    def set_term_base(self, term_base):
        """设置术语库"""
        self.translation_engine.set_term_base(term_base)
        
    def load_term_database(self):
        """加载术语库"""
        # 这个方法保留是为了兼容旧代码
        self.terms = self.translation_engine._load_terms()
        return len(self.terms) > 0
    
    def answer_knowledge_question(self, question, max_knowledge_items=3):
        """使用知识库回答问题，转发到知识库引擎"""
        return self.knowledge_engine.answer_question(question, max_knowledge_items)
    
    def set_persona(self, persona):
        """设置聊天人设，转发到聊天引擎"""
        return self.chat_engine.set_persona(persona)
