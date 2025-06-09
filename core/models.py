#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型响应和配置相关类定义
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass


class MessageResponse:
    """表示模型生成的响应"""
    
    def __init__(self, content: str, generation_time: float = 0.0, metadata: Optional[Dict[str, Any]] = None):
        """
        初始化响应对象
        
        参数:
            content: 响应内容
            generation_time: 生成响应所需的时间（秒）
            metadata: 可选的元数据，如token统计、知识库检索结果等
        """
        self.content = content
        self.generation_time = generation_time
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """将响应转换为字典格式"""
        return {
            "content": self.content,
            "generation_time": self.generation_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageResponse':
        """从字典创建响应对象"""
        return cls(
            content=data.get("content", ""),
            generation_time=data.get("generation_time", 0.0),
            metadata=data.get("metadata", {})
        )
    
    def __repr__(self) -> str:
        """响应的字符串表示"""
        return f"MessageResponse(content='{self.content[:30]}...', time={self.generation_time:.2f}s)"


@dataclass
class GenerationConfig:
    """模型生成配置"""
    
    max_new_tokens: int = 512       # 生成的最大令牌数
    temperature: float = 0.7        # 温度参数，控制随机性
    top_p: float = 0.9              # top-p采样参数
    top_k: int = 0                  # top-k采样参数，0表示禁用
    repetition_penalty: float = 1.1 # 重复惩罚系数
    do_sample: bool = True          # 是否使用采样
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典格式"""
        return {
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repetition_penalty": self.repetition_penalty,
            "do_sample": self.do_sample
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationConfig':
        """从字典创建配置对象"""
        return cls(
            max_new_tokens=data.get("max_new_tokens", 512),
            temperature=data.get("temperature", 0.7),
            top_p=data.get("top_p", 0.9),
            top_k=data.get("top_k", 0),
            repetition_penalty=data.get("repetition_penalty", 1.1),
            do_sample=data.get("do_sample", True)
        ) 