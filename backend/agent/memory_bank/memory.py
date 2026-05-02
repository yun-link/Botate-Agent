"""
Memory Pydantic 模型，定义记忆的数据结构和格式化方法
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json

from pydantic import BaseModel, Field, model_validator
import numpy as np

from model.message_schemas import Message, Text, FunctionCallContent


class Memory(BaseModel):
    """
    记忆类
    
    表示单条记忆，包含文本内容、向量、权重、关联记忆等信息
    """
    
    # 记忆ID（UUID4）
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # 消息列表原始数据
    messages: List[Message] = Field(default_factory=list)
    
    # 文本内容（格式化后的字符串）
    text_content: str = ""
    
    # 关联记忆ID列表
    related_memory_ids: List[str] = Field(default_factory=list)
    
    # 创建时间
    created_at: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 更新时间
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def format_text_content(self) -> str:
        """
        格式化记忆的文本内容
        
        格式：
        Messages: 
        时间（{YYYY mm.DD HH:MM}）-角色：内容
        时间（{YYYY mm.DD HH:MM}）-角色：内容
        ...
        
        Returns:
            格式化后的文本内容
        """
        parts = []
    
        # 添加消息部分
        if self.messages:
            message_lines = []
            for msg in self.messages:
                # 解析消息时间、角色和内容
                timestamp = msg.timestamp
                role = msg.role
                
                # 处理内容
                content_str = self._format_content(msg.content)
                
                # 处理时间格式
                formatted_time = self._format_timestamp(timestamp)
                
                message_lines.append(f"{formatted_time}-{role}：{content_str}"[:512])
            
            if message_lines:
                parts.append("Messages:")
                parts.extend(message_lines)
        
        return ("\n".join(parts))
    
    def _format_timestamp(self, timestamp: str) -> str:
        """
        将时间戳格式化为 'YYYY mm.DD HH:MM' 格式
        
        Args:
            timestamp: 原始时间字符串
            
        Returns:
            格式化后的时间字符串
        """
        try:
            # 尝试解析多种可能的时间格式
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S']:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    return dt.strftime('%Y %m.%d %H:%M')
                except ValueError:
                    continue
            
            # 如果无法解析，返回原始时间
            return timestamp
        except Exception:
            return timestamp
    
    def _format_content(self, content: Any) -> str:
        """
        格式化消息内容
        
        记忆库只支持纯文本内容（str 或 Text 对象），
        其他类型（如多模态内容）将抛出 TypeError。
        
        Args:
            content: 消息内容（必须是 str 或 Text 类型）
            
        Returns:
            格式化后的内容字符串
            
        Raises:
            TypeError: 当内容不是 str 或 Text 类型时
        """
        
        
        if isinstance(content, str):
            return content
        elif isinstance(content, Text):
            # 处理 Text 对象
            return content.content
        elif isinstance(content, list):
            # 处理内容列表，将所有文本内容拼接
            result = []
            for item in content:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, Text):
                    result.append(item.content)
                else:
                    raise TypeError(
                        f"记忆库只支持纯文本内容（str 或 Text 类型），"
                        f"不支持类型: {type(item)}。"
                        f"请确保传入的 Message content 为纯文本。"
                    )
            return " ".join(result)
        elif isinstance(content, FunctionCallContent):
            return f'[Function Call] {content.name}: {content.params} - {content.result}'
        else:
            raise TypeError(
                f"记忆库只支持纯文本内容（str 或 Text 类型），"
                f"不支持类型: {type(content)}。"
                f"请确保传入的 Message content 为纯文本。"
            )
    
    def update_text_content(self) -> None:
        """更新文本内容"""
        self.text_content = self.format_text_content()
    
    def __str__(self) -> str:
        """返回格式化的记忆字符串"""
        return self.text_content if self.text_content else self.format_text_content()
    
    def __repr__(self) -> str:
        return f"Memory(id={self.id[:8]}..., weight={self.weight}, related_count={len(self.related_memory_ids)})"
    
    @model_validator(mode='after')
    def initialize_after_creation(self):
        self.update_text_content()
        return self
