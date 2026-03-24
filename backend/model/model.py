from typing import Any, Dict, List, Optional, Generator, Union, AsyncGenerator
import os
from dataclasses import dataclass

from pydantic import BaseModel
import numpy as np

from .providers.base_provider import BaseProvider, BaseEmbeddingModel, BaseRerankerModel, providers_registry
from .providers.provider_model_info import (
    get_all_providers,
    get_all_models,
    get_provider_info,
    ModelInfo,
    EmbeddingModelInfo,
    RerankerModelInfo,
    ModelType
)
from .message_schemas import Message, ResponseContent, FunctionCallContent, Content
from .tool import Tool
from config.config import ModelConfig

@dataclass
class ModelEntry:
    """模型注册条目"""
    provider_name: str
    model_type: str
    model_info: Union[ModelInfo, EmbeddingModelInfo, RerankerModelInfo]
    loader_method: str

class ProviderRegistry:
    """
    统一的提供商和模型注册表
    
    单例模式，管理所有提供商实例和模型注册信息
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 提供商实例缓存：{provider_name: provider_instance}
        self._providers: Dict[str, BaseProvider] = {}
        
        # 模型注册表：{model_name: ModelEntry}
        self._model_registry: Dict[str, ModelEntry] = {}
        
        # 初始化所有提供商
        self._init_all_providers()
    
    def _init_all_providers(self):
        """从 JSON 配置初始化所有提供商并注册其所有模型"""
        all_models = get_all_models()
        for provider_info in get_all_providers():
            provider_name = provider_info.provider_name
            env_key_name = f'{provider_name.upper()}_API_KEY'
            api_key = os.getenv(env_key_name)

            if not api_key:
                continue
            
            try:
                provider = providers_registry[provider_info.provider_type](
                    base_url=provider_info.base_url,
                    api_key=api_key,
                    model_info_config=provider_info.models
                )
                self._providers[provider_name] = provider

                for model_name, model_info_prov_type in all_models[provider_name].items():
                    prov, info, type = model_info_prov_type
                    # 使用小写键存储，实现大小写不敏感
                    self._model_registry[model_name.lower()] = ModelEntry(
                        provider_name=provider_name,
                        model_type=type,
                        model_info=info,
                        loader_method=f"load_{type}"
                    )
                        
            except Exception as e:
                print(f"初始化提供商 {provider_name} 失败：{e}")
                raise e from e
    
    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """获取提供商实例"""
        return self._providers.get(provider_name)
    
    def get_model_entry(self, model_name: str) -> Optional[ModelEntry]:
        """获取模型注册条目（大小写不敏感）"""
        return self._model_registry.get(model_name.lower())
    
    def get_provider_for_model(self, model_name: str) -> Optional[BaseProvider]:
        """获取能调用指定模型的提供商（大小写不敏感）"""
        entry = self._model_registry.get(model_name.lower())
        if entry:
            return self._providers.get(entry.provider_name)
        return None
    
    def load_model_instance(self, model_name: str, **kwargs):
        """
        加载模型实例（大小写不敏感）
        
        Args:
            model_name: 模型名称
            **kwargs: 传递给加载方法的参数
            
        Returns:
            模型实例
        """
        entry = self._model_registry.get(model_name.lower())
        if not entry:
            raise ValueError(f"找不到模型 {model_name}")
        
        provider = self._providers.get(entry.provider_name)
        if not provider:
            raise ValueError(f"找不到提供商 {entry.provider_name}")
        
        loader = getattr(provider, entry.loader_method)
        return loader(model_name, **kwargs)
    
    def list_models_by_type(self, model_type: str) -> List[str]:
        """列出指定类型的所有模型"""
        return [
            name for name, entry in self._model_registry.items()
            if entry.model_type == model_type
        ]
    
    def list_all_providers(self):
        """列出所有可用提供商"""
        return get_all_providers()

    def list_all_embedding_models(self) -> Dict[str, tuple]:
        """列出所有可用嵌入向量模型"""
        return {
            name: (entry.provider_name, entry.model_info)
            for name, entry in self._model_registry.items()
            if entry.model_type == ModelType.EMBEDDING
        }

    def list_all_reranker_models(self) -> Dict[str, tuple]:
        """列出所有可用重排序模型"""
        return {
            name: (entry.provider_name, entry.model_info)
            for name, entry in self._model_registry.items()
            if entry.model_type == ModelType.RERANKER
        }

    def get_original_model_name(self, model_name: str) -> Optional[str]:
        """获取模型的原始名称（用于大小写不敏感查找后返回原始名称）"""
        entry = self._model_registry.get(model_name.lower())
        if entry:
            # 从注册表中找到原始名称
            for name, e in self._model_registry.items():
                if e is entry:
                    return name
        return None


# 全局注册表实例
_registry = ProviderRegistry()

class Model:
    def __init__(
        self,
        model_name: str,
        system_prompt: str = "",
        tools: Optional[List[Union[Tool, Dict]]] = None
    ):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.tools = tools or []
        
        # 将 Tool 对象列表转换为 OpenAI 格式的 schema 列表
        tools_schema = self._convert_tools_to_schema(self.tools)
        
        prov = _registry.get_provider_for_model(model_name)
        if not prov:
            raise ValueError(f"找不到能调用模型 {model_name} 的提供商")

        self.model_instance = prov.load_model(
            model_name=model_name,
            tools=tools_schema,
            system_prompt=system_prompt
        )
        self.messages = self.model_instance.messages

    def _convert_tools_to_schema(self, tools: List[Union[Tool, Dict]]) -> Optional[List[Dict]]:
        """
        将 Tool 对象列表转换为 OpenAI 格式的 schema 列表
        
        Args:
            tools: Tool 对象列表或字典列表
            
        Returns:
            OpenAI 格式的 schema 列表，如果 tools 为空则返回 None
        """
        if not tools:
            return None
        
        result = []
        for tool in tools:
            if isinstance(tool, Tool):
                result.append(tool.schema.to_openai_format())
            elif isinstance(tool, dict):
                # 兼容旧的字典格式
                result.append(tool)
            else:
                raise ValueError(f"Unsupported tool type: {type(tool)}")
        return result

    def call_model(
        self,
        temperature: float = 0.5,
        top_p: float = 0.1,
        frequency_penalty: float = 0.5,
        thinking: Any = True
    ) -> Generator[ResponseContent, None, None]:
        for chunk in self.model_instance.call_model(
            temperature=temperature,
            top_p=top_p,
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
    ) -> AsyncGenerator[ResponseContent, None]:
        """异步版本的 call_model"""
        async for chunk in self.model_instance.call_model_async(
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            thinking=thinking
        ):
            yield chunk

    def add_message(self, message: Message):
        self.model_instance.add_message(message)
        
    def clear_messages(self):
        self.model_instance.messages = []
    
    @classmethod
    def from_model_config(cls, config: ModelConfig, *args, **kwargs):
        return cls(
            config.model_name,
            *args,
            **kwargs
        )


def get_model_info(model_name):
    """获取模型信息"""
    all_models = get_all_models()
    if model_name not in all_models:
        raise ValueError(f"找不到模型 {model_name}")
    provider_name, model_info = all_models[model_name]
    return model_info


def call(
    model_name,
    messages,
    tools: Optional[List[Union[Tool, Dict]]] = None,
    temperature: float = 0.5,
    top_p: float = 0.1,
    frequency_penalty: float = 0.5,
    thinking: Any = True,
    stream: bool = False
):
    """直接调用模型"""
    prov = _registry.get_provider_for_model(model_name)
    if not prov:
        raise ValueError(f"找不到能调用模型 {model_name} 的提供商")
    
    # 将 Tool 对象列表转换为 OpenAI 格式的 schema 列表
    tools_schema = None
    if tools:
        tools_schema = []
        for tool in tools:
            if isinstance(tool, Tool):
                tools_schema.append(tool.schema.to_openai_format())
            elif isinstance(tool, dict):
                tools_schema.append(tool)
            else:
                raise ValueError(f"Unsupported tool type: {type(tool)}")
    
    return prov.call(
        model_name,
        messages,
        tools_schema,
        temperature,
        top_p,
        frequency_penalty,
        thinking,
        stream
    )


async def call_async(
    model_name,
    messages,
    tools: Optional[List[Union[Tool, Dict]]] = None,
    temperature: float = 0.5,
    top_p: float = 0.1,
    frequency_penalty: float = 0.5,
    thinking: Any = True,
    stream: bool = False
):
    """异步版本的直接调用模型函数"""
    prov = _registry.get_provider_for_model(model_name)
    if not prov:
        raise ValueError(f"找不到能调用模型 {model_name} 的提供商")
    
    # 将 Tool 对象列表转换为 OpenAI 格式的 schema 列表
    tools_schema = None
    if tools:
        tools_schema = []
        for tool in tools:
            if isinstance(tool, Tool):
                tools_schema.append(tool.schema.to_openai_format())
            elif isinstance(tool, dict):
                tools_schema.append(tool)
            else:
                raise ValueError(f"Unsupported tool type: {type(tool)}")
    
    return await prov.call_async(
        model_name,
        messages,
        tools_schema,
        temperature,
        top_p,
        frequency_penalty,
        thinking,
        stream
    )


def list_all_models() -> Dict[str, tuple]:
    """列出所有可用模型及其提供商信息"""
    return _registry.list_all_models()


def list_all_providers():
    """列出所有可用提供商"""
    return _registry.list_all_providers()

class EmbeddingModel:
    """嵌入向量模型类，用于一键调用不同的嵌入模型"""
    
    def __init__(self, model_name: str):
        """
        初始化嵌入向量模型
        
        Args:
            model_name: 模型名称（如 'text-embedding-3-small'）
        """
        self.model_name = model_name
        
        # 获取模型信息
        model_info = _registry.get_model_entry(model_name).model_info
        if not model_info:
            raise ValueError(f"找不到嵌入向量模型 {model_name}")
        
        self.model_id = model_info.model_id
        self.model_display_name = model_name
        
        # 通过注册表获取提供商
        prov = _registry.get_provider_for_model(model_name)
        if not prov:
            raise ValueError(f"找不到能调用嵌入向量模型 {model_name} 的提供商")
        
        # 通过 Provider 加载嵌入模型实例
        self.embedding_instance = prov.load_embedding_model(model_name)

    def encode(self, texts: Union[str, Content, List[Union[str, Content]]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        将文本转换为嵌入向量
        
        Args:
            texts: 单个文本字符串或 Content 对象，或它们的列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        return self.embedding_instance.encode(texts)

    async def encode_async(self, texts: Union[str, Content, List[Union[str, Content]]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        异步版本的文本向量化
        
        Args:
            texts: 单个文本字符串或 Content 对象，或它们的列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        return await self.embedding_instance.encode_async(texts)


def embed(
    model_name: str,
    texts: Union[str, Content, List[Union[str, Content]]]
) -> Union[np.ndarray, List[np.ndarray]]:
    """
    直接调用嵌入向量模型
    
    Args:
        model_name: 模型名称
        texts: 单个文本字符串或 Content 对象，或它们的列表
        
    Returns:
        单个向量 (numpy 数组) 或向量列表
    """
    prov = _registry.get_provider_for_model(model_name)
    if not prov:
        raise ValueError(f"找不到能调用嵌入向量模型 {model_name} 的提供商")
    
    embedding_instance = prov.load_embedding_model(model_name)
    return embedding_instance.encode(texts)


async def embed_async(
    model_name: str,
    texts: Union[str, Content, List[Union[str, Content]]]
) -> Union[np.ndarray, List[np.ndarray]]:
    """
    异步版本的直接调用嵌入向量模型
    
    Args:
        model_name: 模型名称
        texts: 单个文本字符串或 Content 对象，或它们的列表
        
    Returns:
        单个向量 (numpy 数组) 或向量列表
    """
    prov = _registry.get_provider_for_model(model_name)
    if not prov:
        raise ValueError(f"找不到能调用嵌入向量模型 {model_name} 的提供商")
    
    embedding_instance = prov.load_embedding_model(model_name)
    return await embedding_instance.encode_async(texts)


def list_all_embedding_models() -> Dict[str, tuple]:
    """列出所有可用嵌入向量模型及其提供商信息"""
    return _registry.list_all_embedding_models()


class RerankerModel:
    """重排序模型类，用于一键调用不同的重排序模型"""
    
    def __init__(self, model_name: str):
        """
        初始化重排序模型
        
        Args:
            model_name: 模型名称（如 'bge-reranker-v2-m3'）
        """
        self.model_name = model_name
        
        # 获取模型信息
        model_info = _registry.get_model_entry(model_name).model_info
        if not model_info:
            raise ValueError(f"找不到重排序模型 {model_name}")
        
        self.model_id = model_info.model_id
        self.model_display_name = model_name
        
        # 通过注册表获取提供商
        prov = _registry.get_provider_for_model(model_name)
        if not prov:
            raise ValueError(f"找不到能调用重排序模型 {model_name} 的提供商")
        
        # 通过 Provider 加载重排序模型实例
        self.reranker_instance = prov.load_reranker_model(model_name)

    def rerank(
        self, 
        query: Union[str, Content], 
        documents: List[Union[str, Content]], 
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        对文档列表进行重排序
        
        Args:
            query: 查询文本或 Content 对象
            documents: 待排序的文档列表（字符串或 Content 对象）
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        return self.reranker_instance.rerank(query, documents, top_k)

    async def rerank_async(
        self, 
        query: Union[str, Content], 
        documents: List[Union[str, Content]], 
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        异步版本的重排序
        
        Args:
            query: 查询文本或 Content 对象
            documents: 待排序的文档列表（字符串或 Content 对象）
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        return await self.reranker_instance.rerank_async(query, documents, top_k)


def rerank(
    model_name: str,
    query: Union[str, Content],
    documents: List[Union[str, Content]],
    top_k: int = None
) -> List[Dict[str, Any]]:
    """
    直接调用重排序模型
    
    Args:
        model_name: 模型名称
        query: 查询文本或 Content 对象
        documents: 待排序的文档列表（字符串或 Content 对象）
        top_k: 返回前 K 个结果，如果为 None 则返回所有结果
        
    Returns:
        排序后的结果列表，每个结果包含：
        - index: 原始文档索引
        - score: 相关性分数
        - document: 文档内容
    """
    prov = _registry.get_provider_for_model(model_name)
    if not prov:
        raise ValueError(f"找不到能调用重排序模型 {model_name} 的提供商")
    
    reranker_instance = prov.load_reranker_model(model_name)
    return reranker_instance.rerank(query, documents, top_k)


async def rerank_async(
    model_name: str,
    query: Union[str, Content],
    documents: List[Union[str, Content]],
    top_k: int = None
) -> List[Dict[str, Any]]:
    """
    异步版本的直接调用重排序模型
    
    Args:
        model_name: 模型名称
        query: 查询文本或 Content 对象
        documents: 待排序的文档列表（字符串或 Content 对象）
        top_k: 返回前 K 个结果，如果为 None 则返回所有结果
        
    Returns:
        排序后的结果列表，每个结果包含：
        - index: 原始文档索引
        - score: 相关性分数
        - document: 文档内容
    """
    prov = _registry.get_provider_for_model(model_name)
    if not prov:
        raise ValueError(f"找不到能调用重排序模型 {model_name} 的提供商")
    
    reranker_instance = prov.load_reranker_model(model_name)
    return await reranker_instance.rerank_async(query, documents, top_k)


def list_all_reranker_models() -> Dict[str, tuple]:
    """列出所有可用重排序模型及其提供商信息"""
    return _registry.list_all_reranker_models()
