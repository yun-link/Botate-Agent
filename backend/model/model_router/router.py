import json
from typing import Callable, Generator, List, Tuple, Optional, Union, Dict, AsyncGenerator
from dataclasses import dataclass, field

from pydantic import BaseModel

from ..message_schemas import (
    FunctionCallContent, 
    Message, 
    ResponseContent,
    Text,
    Image,
    Audio,
    Video
)
from ..providers import ModelInfo, ThinkingConfig
from ..model import Model, get_model_info, call as call_model, call_async as call_model_async
from ..tool import Tool
from .router_strategies import ModelRouteCache, effectiveness_first, balance, cost_first
from config.config import ModelRouterConfig

router_strategies = {
    "effectiveness_first": effectiveness_first, 
    "balance":  balance, 
    "cost_first": cost_first
}



class ModelRouter:
    def __init__(
        self,
        model_names: List[str],
        rout_func: Callable,
        tools: Optional[List[Union[Tool, Dict]]] = None,
        system_prompt = None
    ):
        self.models = {}
        self.model_names = model_names
        self.model_infos = [get_model_info(model_name) for model_name in model_names]
        self.rout_func = rout_func
        self.messages = []
        self.system_prompt = system_prompt
        self.tools = tools
        self._cache = None

    def call_model(
        self,
        temperature: float = 0.5,
        top_p: float = 0.1,
        frequency_penalty: float = 0.5
    ) -> Generator[ResponseContent | Tuple, None, None]:
        idx, thinking = self.rout_func(self.messages, self.model_infos, self._cache)
        model_id = self.model_infos[idx].model_id
        if model_id not in self.models:
            self.models[model_id] = Model(
                self.model_names[idx],
                self.system_prompt,
                self.tools
            )
            self.models[model_id].model_instance.messages = self.messages
            self.models[model_id].model_instance.tools = self.tools
        yield model_id, thinking
        response = self.models[model_id].call_model(
            temperature,
            top_p,
            frequency_penalty,
            thinking
        )
        self._cache = ModelRouteCache(self.messages, (idx, thinking))
        for chunk in response:
            yield chunk 

    async def call_model_async(
        self,
        temperature: float = 0.5,
        top_p: float = 0.1,
        frequency_penalty: float = 0.5
    ) -> AsyncGenerator[ResponseContent | Tuple, None]:
        """异步版本的 call_model"""
        idx, thinking = self.rout_func(self.messages, self.model_infos, self._cache)
        model_id = self.model_infos[idx].model_id
        if model_id not in self.models:
            self.models[model_id] = Model(
                self.model_names[idx],
                self.system_prompt,
                self.tools
            )
            self.models[model_id].model_instance.messages = self.messages
        yield model_id, thinking
        response = self.models[model_id].call_model_async(
            temperature,
            top_p,
            frequency_penalty,
            thinking
        )
        self._cache = ModelRouteCache(self.messages, (idx, thinking))
        async for chunk in response:
            yield chunk

    def add_message(self, message: Message):
        self.messages.append(message)

    def clear_messages(self):
        self.messages = []

    
    @classmethod
    def from_model_router_config(cls, config: ModelRouterConfig, *args, **kwargs):
        return cls(
            config.model_names,
            router_strategies[config.router_strategies],
            *args,
            **kwargs
        )

def call(
    model_names: List[str],
    rout_func: Callable,
    messages: List[Message],
    tools: Optional[List[Union[Tool, Dict]]] = None,
    temperature: float = 0.5,
    top_p: float = 0.1,
    frequency_penalty: float = 0.5,
    stream: bool = False
):
    """单次调用模型路由器"""
    idx, thinking = rout_func(messages, [get_model_info(name) for name in model_names], None)
    return call_model(
        model_names[idx],
        messages,
        tools,
        temperature,
        top_p,
        frequency_penalty,
        thinking,
        stream
    )

async def call_async(
    model_names: List[str],
    rout_func: Callable,
    messages: List[Message],
    tools: Optional[List[Union[Tool, Dict]]] = None,
    temperature: float = 0.5,
    top_p: float = 0.1,
    frequency_penalty: float = 0.5,
    stream: bool = False
):
    """异步版本的单次调用模型路由器"""
    idx, thinking = rout_func(messages, [get_model_info(name) for name in model_names], None)
    return await call_model_async(
        model_names[idx],
        messages,
        tools,
        temperature,
        top_p,
        frequency_penalty,
        thinking,
        stream
    )
