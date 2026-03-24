from abc import ABC, abstractmethod
from typing import Any, List, Union, Dict, Type
import numpy as np

from ..message_schemas import Content, Text

providers_registry: Dict[str, 'BaseProvider'] = {}


class BaseProvider(ABC):
    """提供商基类"""
    provider_type: str
    @abstractmethod
    def list_models(self) -> List[str]:
        """列出所有可用模型"""
        pass
    
    def get_model_info(self, model_name: str):
        """获取模型信息"""
        return self.model_list.get(model_name)

def registry_provider(provider_class: Type[BaseProvider]):
    providers_registry[provider_class.provider_type] = provider_class

class BaseModel(ABC):
    """模型基类"""
    
    @abstractmethod
    def call_model(self):
        """调用模型"""
        pass

    @abstractmethod
    def add_message(self):
        """添加消息"""
        pass


class BaseEmbeddingModel(ABC):
    """嵌入向量模型基类"""
    
    @abstractmethod
    def encode(self, contents: Union[str, Content, List[Union[str, Content]]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        将内容转换为嵌入向量
        
        Args:
            contents: 单个内容（字符串或 Content 对象）或内容列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        pass
    
    @abstractmethod
    def encode_async(self, contents: Union[str, Content, List[Union[str, Content]]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        异步版本的内容向量化
        
        Args:
            contents: 单个内容（字符串或 Content 对象）或内容列表
            
        Returns:
            单个向量 (numpy 数组) 或向量列表
        """
        pass


class BaseRerankerModel(ABC):
    """重排序模型基类"""
    
    @abstractmethod
    def rerank(
        self, 
        query: Union[str, Content], 
        documents: List[Union[str, Content]], 
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        对文档列表进行重排序
        
        Args:
            query: 查询内容（字符串或 Content 对象）
            documents: 待排序的文档列表（字符串或 Content 对象）
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        pass
    
    @abstractmethod
    async def rerank_async(
        self, 
        query: Union[str, Content], 
        documents: List[Union[str, Content]], 
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        异步版本的重排序
        
        Args:
            query: 查询内容（字符串或 Content 对象）
            documents: 待排序的文档列表（字符串或 Content 对象）
            top_k: 返回前 K 个结果，如果为 None 则返回所有结果
            
        Returns:
            排序后的结果列表，每个结果包含：
            - index: 原始文档索引
            - score: 相关性分数
            - document: 文档内容
        """
        pass
