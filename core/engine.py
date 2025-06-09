#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础消息和角色定义模块
"""

from typing import Dict, Any, Optional, List, Union


class MessageRole:
    """消息角色常量定义"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Message:
    """表示一条对话消息"""
    
    def __init__(self, role: str, content: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        初始化消息对象
        
        参数:
            role: 消息角色，可以是 'system', 'user', 'assistant', 'function'
            content: 消息内容
            name: 可选的消息名称，用于函数调用
            metadata: 可选的元数据
        """
        self.role = role
        self.content = content
        self.name = name
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """将消息转换为字典格式"""
        message_dict = {
            "role": self.role,
            "content": self.content
        }
        
        if self.name is not None:
            message_dict["name"] = self.name
            
        if self.metadata:
            message_dict["metadata"] = self.metadata
            
        return message_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息对象"""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            name=data.get("name"),
            metadata=data.get("metadata")
        )
    
    def __repr__(self) -> str:
        """消息的字符串表示"""
        return f"Message(role='{self.role}', content='{self.content[:30]}...')" 