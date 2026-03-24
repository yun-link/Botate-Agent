"""
API 数据模型

定义 FastAPI 请求和响应的 Pydantic 模型
"""

from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field
from datetime import datetime

from model.message_schemas import (
    Message,
    Text,
    Image,
    Video,
    Audio,
    Content,
    InputContentType
)


class AgentCallRequest(BaseModel):
    """
    调用 Agent 请求模型
    """
    contents: List[InputContentType] = Field(..., description="用户输入的内容列表，支持多模态")


class AgentCallResponse(BaseModel):
    """调用 Agent 响应模型"""
    chunk: InputContentType


class PermissionConfirmRequest(BaseModel):
    """
    权限确认请求模型
    
    用于确认权限不足的操作
    """
    allowed: bool = Field(..., description="是否允许执行该操作")
