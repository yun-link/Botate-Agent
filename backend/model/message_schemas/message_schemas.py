from pydantic import BaseModel, Field, model_validator
import datetime
from abc import ABC, abstractmethod
import os
from typing import Any, Dict, Literal, Optional, Union, List
import uuid
from ._utils import _to_base64, _audio_to_text

class Content(ABC, BaseModel):
    @abstractmethod
    def to_text(self):
        pass

    def __eq__(self, other):
        if hasattr(other, 'content') and hasattr(other, 'type'):
            if other.content == self.content and other.type == self.type:
                return True
        return False
class MultimodalContent(Content, BaseModel):
    """多模态内容基类，提供 base64 转换和 URL 转换的通用方法"""
    content_type: str
    type: Literal['file'] | Literal['url']
    content: str
    _base64_code: Optional[str] = None

    def to_base64(self):
        """将文件内容转换为 base64 编码"""
        if self.type == 'file':
            if self._base64_code is None:
                _, format = os.path.splitext(self.content)
                self._base64_code = f"data:{format.replace('.', '').lower()};base64,{_to_base64(self.content)}"
            return self._base64_code
        return None

    def _get_content_for_text(self) -> Any:
        """获取用于转换为文本的内容，子类可重写此方法"""
        if self.type == 'file':
            return self.to_base64()
        return self.content
    
    def to_text(self):
        """将多模态内容转换为文本描述（带缓存机制）"""
        return self.__str__()
    


class Text(Content, BaseModel):
    content_type: Literal['text'] = 'text'
    content: str
    
    def to_text(self):
        return self.content
    
    def to_dict(self):
        return {'type': 'text', 'text': self.content}
    
    def __eq__(self, other):
        if hasattr(other, 'content') and other.content == self.content:
            return True
        return False


class Image(MultimodalContent):
    content_type: Literal['image'] = 'image'
    
    def to_dict(self):
        if self.type == 'file':
            content = self.to_base64()
        else:
            content = self.content
        return {'type': 'image_url', 'image_url': content}


class Video(MultimodalContent):
    content_type: Literal['video'] = 'video'
    fps: int = 3
    
    def to_dict(self):
        if self.type == 'file':
            content = self.to_base64()
        else:
            content = self.content
        return {'type': 'video_url', 'video_url': {'url': content, 'fps': self.fps}}


class Audio(MultimodalContent):
    content_type: Literal['audio'] = 'audio'
    type: Literal['file'] = 'file'  # Audio 只支持 file 类型
    
    def _generate_text(self, content: Any) -> str:
        length = os.path.getsize(self.content)
        return _audio_to_text(content, length)
    
    def to_dict(self):
        content = self.to_base64()
        return {'type': 'audio', 'audio': content}

class ResponseContent(BaseModel):
    pass

class FunctionCallContent(ResponseContent):
    type: Literal['function_call'] = 'function_call'
    name: str
    params: str | Dict[str, Any]
    id: str
    index: int = 0
    result: Optional[str] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': 'function',
            'function': {
                'name': self.name,
                'arguments': self.params
            }
        }
    
InputContentType = Union[Text, Image, Video, Audio, str, FunctionCallContent]

class AnswerContent(ResponseContent):
    type: Literal['answer'] = 'answer'
    content: InputContentType


class ReasoningContent(ResponseContent):
    type: Literal['reasoning'] = 'reasoning'
    content: InputContentType

class Message(BaseModel):
    role: str
    content: Union[InputContentType, List[InputContentType]]
    reasoning_content: Optional[str] = None
    tool_calls: Any = None
    timestamp: str = Field(default_factory=lambda: str(datetime.datetime.now()))
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    @model_validator(mode='after')
    def convert_content(self):
        """将字符串或字符串列表转换为 Text 对象"""
        if isinstance(self.content, str):
            self.content = Text(content=self.content)
        elif isinstance(self.content, list):
            converted_content = []
            for content in self.content:
                if isinstance(content, str):
                    converted_content.append(Text(content=content))
                else:
                    converted_content.append(content)
            self.content = converted_content
        return self
    
    def __eq__(self, other: 'Message'):
        if isinstance(self.content, list) and isinstance(other.content, list):
            for a, b in zip(self.content, other.content):
                if not a == b:
                    return False
            return True
        elif isinstance(self.content, other.content.__class__):
            if self.content == other.content:
                return True
        return False
