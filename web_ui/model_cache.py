"""
模型缓存管理器
避免在 WEB UI 中重复加载模型，提高资源利用效率
"""

import os
import threading
import time
from typing import Optional, Dict, Any

class ModelCache:
    """全局模型缓存管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.ai_assistant = None
        self.load_time = None
        self.load_lock = threading.Lock()
        self.is_loading = False
        
    def get_ai_assistant(self):
        """获取缓存的 AI 助手实例"""
        return self.ai_assistant
    
    def set_ai_assistant(self, assistant):
        """设置 AI 助手实例到缓存"""
        with self.load_lock:
            self.ai_assistant = assistant
            self.load_time = time.time()
            self.is_loading = False
            print(f"松瓷机电AI助手实例已缓存，加载时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.load_time))}")
    
    def is_cached(self):
        """检查是否已有缓存的实例"""
        return self.ai_assistant is not None
    
    def is_currently_loading(self):
        """检查是否正在加载中"""
        return self.is_loading
    
    def set_loading_status(self, status: bool):
        """设置加载状态"""
        with self.load_lock:
            self.is_loading = status
    
    def clear_cache(self):
        """清除缓存"""
        with self.load_lock:
            if self.ai_assistant:
                print("正在清除松瓷机电AI助手缓存...")
                # 这里可以添加清理逻辑，比如释放GPU内存等
                self.ai_assistant = None
                self.load_time = None
                self.is_loading = False
                print("松瓷机电AI助手缓存已清除")
    
    def get_cache_info(self):
        """获取缓存信息"""
        if self.ai_assistant is None:
            return {
                'cached': False,
                'load_time': None,
                'is_loading': self.is_loading
            }
        
        return {
            'cached': True,
            'load_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.load_time)) if self.load_time else None,
            'is_loading': self.is_loading,
            'cache_age_seconds': time.time() - self.load_time if self.load_time else 0
        }

# 全局缓存实例
model_cache = ModelCache()

def get_model_cache():
    """获取全局模型缓存实例"""
    return model_cache
