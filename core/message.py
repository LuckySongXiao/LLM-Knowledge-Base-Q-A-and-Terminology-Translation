#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
消息类定义模块
"""

from typing import Dict, Any, Optional
from datetime import datetime

class MessageRole:
    """消息角色常量"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class Message:
    """消息类，用于表示对话中的一条消息"""
    
    def __init__(self, role: str, content: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        初始化消息对象
        
        Args:
            role: 消息角色，如system, user, assistant
            content: 消息内容
            name: 可选的名称，用于function调用
            metadata: 可选的元数据
        """
        self.role = role
        self.content = content
        self.name = name
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "role": self.role,
            "content": self.content
        }
        if self.name:
            result["name"] = self.name
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息对象"""
        return cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            name=data.get("name"),
            metadata=data.get("metadata")
        )
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.role}] {self.content[:50]}..." if len(self.content) > 50 else f"[{self.role}] {self.content}"

class MessageResponse:
    """消息响应类，用于表示AI生成的响应"""
    
    def __init__(self, content: str, generation_time: float = 0, metadata: Optional[Dict[str, Any]] = None):
        """
        初始化响应对象
        
        Args:
            content: 响应内容
            generation_time: 生成时间(秒)
            metadata: 可选的元数据
        """
        self.content = content
        self.generation_time = generation_time
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_message(self) -> Message:
        """转换为消息对象"""
        return Message(
            role=MessageRole.ASSISTANT,
            content=self.content,
            metadata=self.metadata
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "generation_time": self.generation_time,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageResponse':
        """从字典创建响应对象"""
        return cls(
            content=data.get("content", ""),
            generation_time=data.get("generation_time", 0),
            metadata=data.get("metadata")
        )