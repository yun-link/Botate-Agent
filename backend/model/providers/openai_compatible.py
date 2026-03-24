import json
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
import asyncio

import numpy as np
import requests
import aiohttp
from openai import OpenAI, AsyncOpenAI

from .base_provider import BaseProvider, BaseModel, BaseEmbeddingModel, BaseRerankerModel, registry_provider
from .provider_model_info import ModelInfo, ThinkingConfig, EmbeddingModelInfo, RerankerModelInfo, get_model_info
from ..message_schemas import (
    Message, 
    AnswerContent, 
    ReasoningContent, 
    FunctionCallContent,
    Text,
    Image,
    Video,
    Audio,
    Content
)

def _format_tool_content(content):
    tool_list = []

    if isinstance(content, FunctionCallContent):
        tool_list.append({
            "id": content.id,
            "type": "function",
            "function": {
                "name": content.name,
                "arguments": json.dumps(content.params)
            }
        })
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, FunctionCallContent):
                tool_list.append({
                    "id": item.id,
                    "type": "function",
                    "function": {
                        "name": item.name,
                        "arguments": json.dumps(item.params)
                    }
                })
    return tool_list


def _format_content(content: Union[Content, str], modality_classes: List[type]) -> Union[str, Dict]:
    """
    格式化单个内容对象为 API 可接受的格式
    
    Args:
        content: 内容对象（字符串或 Content 实例）
        modality_classes: 模型支持的模态类型类列表
        
    Returns:
        格式化后的内容（字符串或字典）
    """
    if isinstance(content, str):
        return content
    
    # 如果内容类型在支持的模态范围内，使用 to_dict()
    if isinstance(content, tuple(modality_classes)):
        return content.to_dict()
    else:
        # 不支持的模态类型，转换为文本描述
        return Text(f"{content.__class__.__name__}(content: '{content.to_text()}')").to_dict()


def _format_content_list(contents: Union[str, Content, List[Union[str, Content]]], modality_classes: List[type]) -> Union[str, List[Dict]]:
    """
    格式化内容列表为 API 可接受的格式
    
    Args:
        contents: 内容（单个或列表）
        modality_classes: 模型支持的模态类型类列表
        
    Returns:
        格式化后的内容
    """
    if isinstance(contents, (str, Content)):
        return _format_content(contents, modality_classes)
    
    return [_format_content(c, modality_classes) for c in contents]


def _generate_thinking(thinking, model_info):
    config = {}
    thinking_config = model_info.thinking
    if thinking_config.support_thinking and thinking == True:
        if thinking_config.support_Answer:
            config['thinking'] = thinking_config.thinking
        else:
            pass
    elif thinking_config.support_auto and thinking == 'auto':
        config['thinking'] = thinking_config.auto
    elif thinking_config.support_effort and thinking in thinking_config.effort:
        config['reasoning_effort'] = thinking_config.effort[thinking]
    elif thinking_config.support_Answer and not thinking_config.support_thinking:
        pass
    else:
        config['thinking'] = thinking_config.Answer
    return {'extra_body': config}


def _format_messages(messages, model_info):
    f_messages = []
    modality_classes = model_info.get_modality_classes()
    
    for message in messages:
        content = ""
        tool_call_id = None
    
        if isinstance(message.content, Text):
            content = message.content.content

        elif isinstance(message.content, list):
            content = _format_content_list(message.content)

        if message.tool_calls or isinstance(message.content, FunctionCallContent):

            if message.role == "assistant":
                msg = {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": _format_tool_content(message.tool_calls or message.content)
                }
                if message.reasoning_content:
                    msg['reasoning_content'] = message.reasoning_content
                f_messages.append(msg)
            elif message.role == "tool":
                f_messages.append({
                    "role": "tool",
                    "content": str(message.content.result or message.tool_calls.result or '工具没有返回结果'),
                    "tool_call_id": message.content.id or message.tool_calls.id
                })
            continue
        msg_dict = {"role": message.role, "content": content}

        if hasattr(message, 'tool_call_id') and message.tool_call_id:
            msg_dict["tool_call_id"] = message.tool_call_id
        
        f_messages.append(msg_dict)
    return f_messages


def _instance_response_stream(response):
    function_name = ""
    function_id = ""
    function_params = ""
    for chunk in response:
        if not chunk.choices:
            continue
            
        delta = chunk.choices[0].delta
        
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            yield ReasoningContent(content=delta.reasoning_content)
        
        if hasattr(delta, 'content') and delta.content:
            yield AnswerContent(content=delta.content)

        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            if delta.tool_calls[0].function.name:
                function_name = delta.tool_calls[0].function.name
                function_id = delta.tool_calls[0].id
                function_index = delta.tool_calls[0].index
                continue
            function_params = delta.tool_calls[0].function.arguments
            yield FunctionCallContent(name=function_name, params=function_params, id=function_id, index=function_index)


async def _instance_response_stream_async(response):
    """异步版本的消息流处理"""
    function_name = ""
    function_id = ""
    function_params = ""
    function_index = 0
    async for chunk in response:
        if not chunk.choices:
            continue
            
        delta = chunk.choices[0].delta
        
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            yield ReasoningContent(content=delta.reasoning_content)
        
        if hasattr(delta, 'content') and delta.content:
            yield AnswerContent(content=delta.content)

        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            if delta.tool_calls[0].function.name:
                function_name = delta.tool_calls[0].function.name
                function_id = delta.tool_calls[0].id
                function_index = delta.tool_calls[0].index
                continue
            function_params = delta.tool_calls[0].function.arguments
            yield FunctionCallContent(name=function_name, params=function_params, id=function_id, index=function_index)


def _instance_response(response):
    message = response.choices[0].message
    content = message.content
    reasoning_content = ''
    tool_calls = []
    if hasattr(message, 'reasoning_content'):
        reasoning_content = message.reasoning_content
    if message.tool_calls:
        for tool_call in message.tool_calls:
            tool_calls.append(
                FunctionCallContent(
                    name=tool_call.function.name,
                    params=tool_call.function.arguments,
                    id=tool_call.id,
                )
            )
    return Message(
        role='assistant', 
        content=content, 
        reasoning_content=reasoning_content, 
        tool_calls=tool_calls
    )


async def _async_instance_response(response):
    """异步版本的响应处理函数"""
    message = response.choices[0].message
    content = message.content
    reasoning_content = ''
    tool_calls = []
    if hasattr(message, 'reasoning_content'):
        reasoning_content = message.reasoning_content
    if message.tool_calls:
        for tool_call in message.tool_calls:
            tool_calls.append(
                FunctionCallContent(
                    name=tool_call.function.name,
                    params=tool_call.function.arguments,
                    id=tool_call.id,
                )
            )
    return Message(
        role='assistant', 
        content=content, 
        reasoning_content=reasoning_content, 
        tool_calls=tool_calls
    )


def _generate_call_config(
    model_info: ModelInfo,
    messages: List[Message],
    temperature: float = 0.5,
    top_p: float = 0.1,
    tools: Optional[List[Dict[str, Any]]] = None,
    frequency_penalty: float = 0.5,
    thinking: Any = True,
    stream: bool = False
):
    config = {
        'model': model_info.model_id,
        'temperature': temperature,
        'top_p': top_p,
        'tools': tools,
        'frequency_penalty': frequency_penalty,
        'messages': _format_messages(messages, model_info),
        'stream': stream,
        'max_tokens': 32768
    }
    config.update(_generate_thinking(thinking, model_info))
    return config


def _encode_once(
    client: OpenAI,
    model_id: str,
    contents: Union[str, Content, List[Union[str, Content]]],
    modality_classes: List[type] = None
) -> Union[np.ndarray, List[np.ndarray]]:
    """
    单次嵌入向量编码调用
    
    Args:
        client: OpenAI 客户端
        model_id: 模型 ID
        contents: 单个内容（字符串或 Content 对象）或内容列表
        modality_classes: 模型支持的模态类型类列表（用于格式化内容）
        
    Returns:
        单个向量 (numpy 数组) 或向量列表
    """
    # 统一处理为列表
    if isinstance(contents, (str, Content)):
        contents = [contents]
    
    # 如果有 modality_classes，使用 _format_content 处理；否则转换为文本
    if modality_classes:
        input_texts = []
        for c in contents:
            formatted = _format_content(c, modality_classes)
            if isinstance(formatted, dict):
                # 如果是字典格式（如图片），提取其中的文本或使用 to_text()
                input_texts.append(str(formatted))
            else:
                input_texts.append(formatted)
    else:
        input_texts = [c.to_text() if isinstance(c, Content) else c for c in contents]
    
    response = client.embeddings.create(
        input=input_texts,
        model=model_id
    )
    
    # 如果原始输入是单个内容，返回单个向量
    if len(contents) == 1:
        return np.array(response.data[0].embedding)
    return [np.array(item.embedding) for item in response.data]


async def _encode_once_async(
    async_client: AsyncOpenAI,
    model_id: str,
    contents: Union[str, Content, List[Union[str, Content]]],
    modality_classes: List[type] = None
) -> Union[np.ndarray, List[np.ndarray]]:
    """
    异步版本的单次嵌入向量编码调用
    
    Args:
        async_client: 异步 OpenAI 客户端
        model_id: 模型 ID
        contents: 单个内容（字符串或 Content 对象）或内容列表
        modality_classes: 模型支持的模态类型类列表（用于格式化内容）
        
    Returns:
        单个向量 (numpy 数组) 或向量列表
    """
    # 统一处理为列表
    if isinstance(contents, (str, Content)):
        contents = [contents]
    
    # 如果有 modality_classes，使用 _format_content 处理；否则转换为文本
    if modality_classes:
        input_texts = []
        for c in contents:
            formatted = _format_content(c, modality_classes)
            if isinstance(formatted, dict):
                input_texts.append(str(formatted))
            else:
                input_texts.append(formatted)
    else:
        input_texts = [c.to_text() if isinstance(c, Content) else c for c in contents]
    
    response = await async_client.embeddings.create(
        input=input_texts,
        model=model_id
    )
    
    # 如果原始输入是单个内容，返回单个向量
    if len(contents) == 1 and not isinstance(contents, list):
        return np.array(response.data[0].embedding)
    return [np.array(item.embedding) for item in response.data]


def _rerank_once(
    base_url: str,
    api_key: str,
    model_id: str,
    query: Union[str, Content],
    documents: List[Union[str, Content]],
    top_k: int = None,
    modality_classes: List[type] = None
) -> List[Dict[str, Any]]:
    """
    单次重排序调用
    
    Args:
        base_url: API 基础 URL
        api_key: API 密钥
        model_id: 模型 ID
        query: 查询内容（字符串或 Content 对象）
        documents: 待排序的文档列表（字符串或 Content 对象）
        top_k: 返回前 K 个结果
        modality_classes: 模型支持的模态类型类列表（用于格式化内容）
        
    Returns:
        排序后的结果列表
    """
    url = f"{base_url}/rerank"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 将 query 和 documents 转换为文本
    if modality_classes:
        query_formatted = _format_content(query, modality_classes)
        query_text = query_formatted if isinstance(query_formatted, str) else query.to_text()
        document_texts = []
        for d in documents:
            formatted = _format_content(d, modality_classes)
            document_texts.append(formatted if isinstance(formatted, str) else d.to_text())
    else:
        query_text = query.to_text() if isinstance(query, Content) else query
        document_texts = [d.to_text() if isinstance(d, Content) else d for d in documents]
    
    payload = {
        "model": model_id,
        "query": query_text,
        "documents": document_texts,
        "top_k": top_k
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_data = response.json()
    
    results = []
    for item in response_data.get("results", []):
        results.append({
            "index": item.get("index", 0),
            "score": item.get("relevance_score", 0),
            "document": documents[item.get("index", 0)]
        })
    
    # 按分数降序排序
    results.sort(key=lambda x: x["score"], reverse=True)
    
    if top_k:
        results = results[:top_k]
    
    return results


async def _rerank_once_async(
    base_url: str,
    api_key: str,
    model_id: str,
    query: Union[str, Content],
    documents: List[Union[str, Content]],
    top_k: int = None,
    modality_classes: List[type] = None
) -> List[Dict[str, Any]]:
    """
    异步版本的单次重排序调用
    
    Args:
        base_url: API 基础 URL
        api_key: API 密钥
        model_id: 模型 ID
        query: 查询内容（字符串或 Content 对象）
        documents: 待排序的文档列表（字符串或 Content 对象）
        top_k: 返回前 K 个结果
        modality_classes: 模型支持的模态类型类列表（用于格式化内容）
        
    Returns:
        排序后的结果列表
    """
    url = f"{base_url}/rerank"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 将 query 和 documents 转换为文本
    if modality_classes:
        query_formatted = _format_content(query, modality_classes)
        query_text = query_formatted if isinstance(query_formatted, str) else query.to_text()
        document_texts = []
        for d in documents:
            formatted = _format_content(d, modality_classes)
            document_texts.append(formatted if isinstance(formatted, str) else d.to_text())
    else:
        query_text = query.to_text() if isinstance(query, Content) else query
        document_texts = [d.to_text() if isinstance(d, Content) else d for d in documents]
    
    payload = {
        "model": model_id,
        "query": query_text,
        "documents": document_texts,
        "top_k": top_k
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()
            response_data = await response.json()
    
    results = []
    for item in response_data.get("results", []):
        results.append({
            "index": item.get("index", 0),
            "score": item.get("relevance_score", 0),
            "document": documents[item.get("index", 0)]
        })
    
    # 按分数降序排序
    results.sort(key=lambda x: x["score"], reverse=True)
    
    if top_k:
        results = results[:top_k]
    
    return results


def _call_once(
    client: OpenAI,
    model_info: ModelInfo,
    messages: List[Message],
    temperature: float = 0.5,
    top_p: float = 0.1,
    tools: Optional[List[Dict[str, Any]]] = None,
    frequency_penalty: float = 0.5,
    thinking: Any = True
) -> Message:
    """
    单次模型调用（非流式）
    
    Args:
        client: OpenAI 客户端
        model_info: 模型信息
        messages: 消息列表
        temperature: 温度参数
        top_p: top_p 参数
        tools: 工具列表
        frequency_penalty: 频率惩罚参数
        thinking: 思考配置
        
    Returns:
        Message 对象
    """
    config = _generate_call_config(
        model_info=model_info,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        tools=tools,
        frequency_penalty=frequency_penalty,
        thinking=thinking,
        stream=False
    )
    response = client.chat.completions.create(**config)
    return _instance_response(response)


async def _call_once_async(
    async_client: AsyncOpenAI,
    model_info: ModelInfo,
    messages: List[Message],
    temperature: float = 0.5,
    top_p: float = 0.1,
    tools: Optional[List[Dict[str, Any]]] = None,
    frequency_penalty: float = 0.5,
    thinking: Any = True
) -> Message:
    """
    异步版本的单次模型调用（非流式）
    
    Args:
        async_client: 异步 OpenAI 客户端
        model_info: 模型信息
        messages: 消息列表
        temperature: 温度参数
        top_p: top_p 参数
        tools: 工具列表
        frequency_penalty: 频率惩罚参数
        thinking: 思考配置
        
    Returns:
        Message 对象
    """
    config = _generate_call_config(
        model_info=model_info,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        tools=tools,
        frequency_penalty=frequency_penalty,
        thinking=thinking,
        stream=False
    )
    response = await async_client.chat.completions.create(**config)
    return await _async_instance_response(response)


def _call_stream_once(
    client: OpenAI,
    model_info: ModelInfo,
    messages: List[Message],
    temperature: float = 0.5,
    top_p: float = 0.1,
    tools: Optional[List[Dict[str, Any]]] = None,
    frequency_penalty: float = 0.5,
    thinking: Any = True
) -> AsyncGenerator:
    """
    单次模型调用（流式）
    
    Args:
        client: OpenAI 客户端
        model_info: 模型信息
        messages: 消息列表
        temperature: 温度参数
        top_p: top_p 参数
        tools: 工具列表
        frequency_penalty: 频率惩罚参数
        thinking: 思考配置
        
    Returns:
        生成器，产生消息内容块
    """
    config = _generate_call_config(
        model_info=model_info,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        tools=tools,
        frequency_penalty=frequency_penalty,
        thinking=thinking,
        stream=True
    )
    response = client.chat.completions.create(**config)
    return _instance_response_stream(response)


async def _call_stream_once_async(
    async_client: AsyncOpenAI,
    model_info: ModelInfo,
    messages: List[Message],
    temperature: float = 0.5,
    top_p: float = 0.1,
    tools: Optional[List[Dict[str, Any]]] = None,
    frequency_penalty: float = 0.5,
    thinking: Any = True
) -> AsyncGenerator:
    """
    异步版本的单次模型调用（流式）
    
    Args:
        async_client: 异步 OpenAI 客户端
        model_info: 模型信息
        messages: 消息列表
        temperature: 温度参数
        top_p: top_p 参数
        tools: 工具列表
        frequency_penalty: 频率惩罚参数
        thinking: 思考配置
        
    Returns:
        异步生成器，产生消息内容块
    """
    config = _generate_call_config(
        model_info=model_info,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        tools=tools,
        frequency_penalty=frequency_penalty,
        thinking=thinking,
        stream=True
    )
    response = await async_client.chat.completions.create(**config)
    async for chunk in _instance_response_stream_async(response):
        yield chunk


class OpenAICompatibleModel(BaseModel):
    """OpenAI 兼容模型基类"""
    
    def __init__(
        self,
        model_info: ModelInfo,
        client: OpenAI,
        async_client: AsyncOpenAI,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: str = "",
    ):
        self.model_info = model_info
        self.client = client
        self.async_client = async_client
        self.messages: List[Message] = []
        self.tools = tools
        if system_prompt:
            self.messages.append(Message(role="system", content=system_prompt))

    def call_model(
        self,
        temperature: float = 0.5,
        top_p: float = 0.1,
        frequency_penalty: float = 0.5,
        thinking: Any = True
    ):
        for chunk in _call_stream_once(
            client=self.client,
            model_info=self.model_info,
            messages=self.messages,
            temperature=temperature,
            top_p=top_p,
            tools=self.tools,
            frequency_penalty=frequency_penalty,
            thinking=thinking
        ):
            yield chunk

    async def call_model_async(
        self,
        temperature: float = 0.5,
        top_p: float = 0.1,
        frequency_penalty: float = 0.5,
        thinking: Any = True
    ) -> AsyncGenerator:
        """异步版本的 call_model"""
        async for chunk in _call_stream_once_async(
            async_client=self.async_client,
            model_info=self.model_info,
            messages=self.messages,
            temperature=temperature,
            top_p=top_p,
            tools=self.tools,
            frequency_penalty=frequency_penalty,
            thinking=thinking
        ):
            yield chunk

    def add_message(self, message: Message):
        self.messages.append(message)
class OpenAICompatibleEmbeddingModel(BaseEmbeddingModel):
    """OpenAI 兼容嵌入向量模型类"""
    
    def __init__(
        self,
        model_id: str,
        client: OpenAI,
        async_client: AsyncOpenAI
    ):
        self.model_id = model_id
        self.client = client
        self.async_client = async_client

    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        将文本转换为嵌入向量
        
        Args:
            texts: 单个文本字符串或文本列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        return _encode_once(self.client, self.model_id, texts)

    async def encode_async(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        异步版本的文本向量化
        
        Args:
            texts: 单个文本字符串或文本列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        return await _encode_once_async(self.async_client, self.model_id, texts)


class OpenAICompatibleRerankerModel(BaseRerankerModel):
    """OpenAI 兼容重排序模型类"""
    
    def __init__(
        self,
        model_id: str,
        base_url: str,
        api_key: str,
    ):
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key

    def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        对文档列表进行重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        return _rerank_once(self.base_url, self.api_key, self.model_id, query, documents, top_k)

    async def rerank_async(
        self, 
        query: str, 
        documents: List[str], 
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        异步版本的重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        return await _rerank_once_async(self.base_url, self.api_key, self.model_id, query, documents, top_k)


class OpenAICompatibleProvider(BaseProvider):
    """OpenAI 兼容提供商基类
    
    支持通过 base_url 和 api_key 初始化，适用于所有 OpenAI 兼容的 API
    """
    provider_type = 'openai_compatible'
    def __init__(
        self, 
        base_url: str, 
        api_key: str, 
        model_info_config: Optional[Dict[str, ModelInfo]] = None
    ):
    
        self.base_url = base_url
        self.api_key = api_key
        self.model_list = model_info_config or {}
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def load_model(
        self,
        model_name: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> OpenAICompatibleModel:
        if model_name not in self.model_list:
            raise ValueError(f"No model name is {model_name}.")
        return OpenAICompatibleModel(
            model_info=self.model_list[model_name],
            client=self.client,
            async_client=self.async_client,
            tools=tools,
            system_prompt=system_prompt or "",
        )

    def call(
        self,
        model_name: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.5,
        top_p: float = 0.1,
        frequency_penalty: float = 0.5,
        thinking: Any = True,
        stream: bool = False
    ):
        """
        调用模型
        
        Args:
            model_name: 模型名称
            messages: 消息列表
            tools: 工具列表
            temperature: 温度参数
            top_p: top_p 参数
            frequency_penalty: 频率惩罚参数
            thinking: 思考配置
            stream: 是否流式输出
            
        Returns:
            Message 对象或生成器
        """
        model_info = self.model_list[model_name]
        if stream:
            return _call_stream_once(
                client=self.client,
                model_info=model_info,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                tools=tools,
                frequency_penalty=frequency_penalty,
                thinking=thinking
            )
        else:
            return _call_once(
                client=self.client,
                model_info=model_info,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                tools=tools,
                frequency_penalty=frequency_penalty,
                thinking=thinking
            )

    async def call_async(
        self,
        model_name: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.5,
        top_p: float = 0.1,
        frequency_penalty: float = 0.5,
        thinking: Any = True,
        stream: bool = False
    ):
        """
        异步版本的 call 函数
        
        Args:
            model_name: 模型名称
            messages: 消息列表
            tools: 工具列表
            temperature: 温度参数
            top_p: top_p 参数
            frequency_penalty: 频率惩罚参数
            thinking: 思考配置
            stream: 是否流式输出
            
        Returns:
            Message 对象或异步生成器
        """
        model_info = self.model_list[model_name]
        if stream:
            return _call_stream_once_async(
                async_client=self.async_client,
                model_info=model_info,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                tools=tools,
                frequency_penalty=frequency_penalty,
                thinking=thinking
            )
        else:
            return await _call_once_async(
                async_client=self.async_client,
                model_info=model_info,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                tools=tools,
                frequency_penalty=frequency_penalty,
                thinking=thinking
            )

    def list_models(self) -> List[str]:
        return list(self.model_list.keys())

    def get_model_info(self, model_name: str) -> ModelInfo:
        return self.model_list[model_name]

    def load_embedding_model(
        self,
        model_name: str
    ) -> OpenAICompatibleEmbeddingModel:
        """
        加载嵌入向量模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            OpenAICompatibleEmbeddingModel 实例
        """
        model_info = self._get_embedding_model_info(model_name)
        return OpenAICompatibleEmbeddingModel(
            model_id=model_info.model_id,
            client=self.client,
            async_client=self.async_client
        )

    def load_reranker_model(
        self,
        model_name: str
    ) -> OpenAICompatibleRerankerModel:
        """
        加载重排序模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            OpenAICompatibleRerankerModel 实例
        """
        model_info = self._get_reranker_model_info(model_name)
        return OpenAICompatibleRerankerModel(
            model_id=model_info.model_id,
            base_url=self.base_url,
            api_key=self.api_key
        )

    def _get_embedding_model_info(self, model_name: str) -> EmbeddingModelInfo:
        """获取嵌入模型信息"""
        model_info = get_model_info(model_name)
        if not model_info:
            raise ValueError(f"找不到嵌入向量模型 {model_name}")
        return model_info

    def _get_reranker_model_info(self, model_name: str) -> RerankerModelInfo:
        """获取重排序模型信息"""
        model_info = get_model_info(model_name)
        if not model_info:
            raise ValueError(f"找不到重排序模型 {model_name}")
        return model_info

    def encode(
        self,
        model_name: str,
        texts: Union[str, List[str]]
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        使用指定嵌入模型编码文本
        
        Args:
            model_name: 模型名称
            texts: 单个文本字符串或文本列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        model_info = self._get_embedding_model_info(model_name)
        return _encode_once(self.client, model_info.model_id, texts)

    async def encode_async(
        self,
        model_name: str,
        texts: Union[str, List[str]]
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        异步版本的文本编码
        
        Args:
            model_name: 模型名称
            texts: 单个文本字符串或文本列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        model_info = self._get_embedding_model_info(model_name)
        return await _encode_once_async(self.async_client, model_info.model_id, texts)

    def rerank(
        self,
        model_name: str,
        query: str,
        documents: List[str],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        使用指定重排序模型对文档进行重排序
        
        Args:
            model_name: 模型名称
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        model_info = self._get_reranker_model_info(model_name)
        return _rerank_once(
            base_url=self.base_url,
            api_key=self.api_key,
            model_id=model_info.model_id,
            query=query,
            documents=documents,
            top_k=top_k
        )

    async def rerank_async(
        self,
        model_name: str,
        query: str,
        documents: List[str],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        异步版本的重排序
        
        Args:
            model_name: 模型名称
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        model_info = self._get_reranker_model_info(model_name)
        return await _rerank_once_async(
            base_url=self.base_url,
            api_key=self.api_key,
            model_id=model_info.model_id,
            query=query,
            documents=documents,
            top_k=top_k
        )

registry_provider(OpenAICompatibleProvider)
