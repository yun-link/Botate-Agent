from typing import Optional
from pydantic import BaseModel


class AnswerBeginEvent(BaseModel):
    """
    回答开始事件
    
    当 Agent 开始生成回答时触发
    """
    type: str = "event"
    event: str = "answer_begin"


class ReasoningBeginEvent(BaseModel):
    """
    推理开始事件
    
    当 Agent 开始进行推理思考时触发
    """
    type: str = "event"
    event: str = "reasoning_begin"


class FunctionCallInfoEvent(BaseModel):
    """
    函数调用信息事件
    
    当 Agent 调用工具时触发，包含工具调用的名字
    
    Attributes:
        tool_name: 被调用的工具名称
    """
    type: str = "event"
    event: str = "function_call_info"
    tool_name: str


class RoundEndEvent(BaseModel):
    """
    轮次结束事件
    
    当 Agent 完成一轮交互时触发
    """
    type: str = "event"
    event: str = "round_end"


class PermissionDeniedEvent(BaseModel):
    """
    权限不足事件
    
    当文件操作权限不足时触发，需要用户确认
    
    Attributes:
        tool_name: 被调用的工具名称
        reason: 拒绝原因
    """
    type: str = "event"
    event: str = "permission_denied"
    tool_name: str
    reason: str


class PermissionConfirmationEvent(BaseModel):
    """
    权限确认事件
    
    用户确认允许执行权限不足的操作
    
    Attributes:
        confirmation_id: 确认ID，对应 PermissionDeniedEvent 中的 confirmation_id
        allowed: 是否允许执行
    """
    type: str = "event"
    event: str = "permission_confirmation"
    confirmation_id: str
    allowed: bool
