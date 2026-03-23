"""
Memory Pydantic 模型，定义记忆的数据结构和格式化方法
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json

from pydantic import BaseModel, Field, model_validator
import numpy as np

from .models import MemoryModel
from model.message_schemas import Message, Text


class Memory(BaseModel):
    """
    记忆类
    
    表示单条记忆，包含文本内容、向量、权重、关联记忆等信息
    """
    
    # 记忆ID（UUID4）
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # 记忆摘要（可选）
    summary: Optional[str] = None
    
    # 消息列表原始数据
    messages: List[Message] = Field(default_factory=list)
    
    # 文本内容（格式化后的字符串）
    text_content: str = ""
    
    # 向量数据（可选）
    vector: Optional[List[float]] = None
    
    # 权重：记忆的重要程度
    weight: float = Field(default=1.0)
    
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
        Summary: {summary}
        Messages: 
        时间（{YYYY mm.DD HH:MM}）-角色：内容
        时间（{YYYY mm.DD HH:MM}）-角色：内容
        ...
        
        如果summary为空或未启用，则不包含Summary部分
        
        Returns:
            格式化后的文本内容
        """
        parts = []
        
        # 添加摘要部分（如果有）
        if self.summary:
            parts.append(f"Summary: {self.summary}")
        
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
                
                message_lines.append(f"{formatted_time}-{role}：{content_str}")
            
            if message_lines:
                parts.append("Messages:")
                parts.extend(message_lines)
        
        return "\n".join(parts)
    
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
        else:
            raise TypeError(
                f"记忆库只支持纯文本内容（str 或 Text 类型），"
                f"不支持类型: {type(content)}。"
                f"请确保传入的 Message content 为纯文本。"
            )
    
    def update_text_content(self) -> None:
        """更新文本内容"""
        self.text_content = self.format_text_content()
    
    @classmethod
    def from_model(cls, model: MemoryModel) -> 'Memory':
        """
        从数据库模型创建Memory实例
        
        Args:
            model: SQLAlchemy MemoryModel 实例
            
        Returns:
            Memory 实例
        """
        # 将字典列表转换为 Message 对象列表
        messages_data = model.messages_data or []
        messages = []
        for msg_dict in messages_data:
            try:
                messages.append(Message(**msg_dict))
            except Exception:
                # 如果转换失败，跳过该消息
                continue
        
        return cls(
            id=model.id,
            summary=model.summary,
            messages=messages,
            text_content=model.text_content,
            vector=model.vector,
            weight=model.weight,
            related_memory_ids=model.related_memory_ids,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def to_model(self) -> MemoryModel:
        """
        转换为数据库模型
        
        Returns:
            SQLAlchemy MemoryModel 实例
        """
        # 将 Message 对象列表转换为字典列表
        messages_data = None
        if self.messages:
            messages_data = [msg.model_dump(exclude_none=True) for msg in self.messages]
        
        model = MemoryModel()
        model.id = self.id
        model.summary = self.summary
        model.messages_data = messages_data
        model.text_content = self.text_content
        model.vector = self.vector.tolist() if hasattr(self.vector, 'tolist') else self.vector
        model.weight = self.weight
        model.related_memory_ids = self.related_memory_ids
        model.created_at = self.created_at
        model.updated_at = self.updated_at
        return model
    
    def __str__(self) -> str:
        """返回格式化的记忆字符串"""
        return self.text_content if self.text_content else self.format_text_content()
    
    def __repr__(self) -> str:
        return f"Memory(id={self.id[:8]}..., weight={self.weight}, related_count={len(self.related_memory_ids)})"
    
    @model_validator(mode='after')
    def initialize_after_creation(self):
        self.update_text_content()
        return self
