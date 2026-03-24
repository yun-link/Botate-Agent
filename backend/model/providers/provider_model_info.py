from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from ..message_schemas import Text, Image, Video, Audio
from config import PATH_CONFIG

# 模态类型映射
MODALITY_MAP = {
    "Text": Text,
    "Image": Image,
    "Video": Video,
    "Audio": Audio
}

# 模型类型常量
class ModelType:
    LLM = "llm"
    EMBEDDING = "embedding"
    RERANKER = "reranker"


class ThinkingConfig(BaseModel):
    """思维链配置"""
    support_thinking: bool
    support_Answer: bool = False
    support_auto: bool = False
    support_effort: bool = False
    thinking: Any = None
    Answer: Any = None
    auto: Any = None
    effort: Any = None


class Performance(BaseModel):
    """性能指标"""
    reasoning: float
    writing: float
    coding: float
    speed: float
    cost: float


class ModelInfo(BaseModel):
    """LLM 模型信息"""
    model_id: str
    thinking: ThinkingConfig
    modality: List[str]
    performance: Optional[Performance] = None
    other: Optional[str] = None

    def get_modality_classes(self) -> List[type]:
        """获取模态类型类列表"""
        return [MODALITY_MAP.get(m, Text) for m in self.modality]


class EmbeddingModelInfo(BaseModel):
    """嵌入向量模型信息"""
    model_id: str
    modality: List[str] = ["Text"]  # 支持的模态类型，默认为文本
    
    def get_modality_classes(self) -> List[type]:
        """获取模态类型类列表"""
        return [MODALITY_MAP.get(m, Text) for m in self.modality]


class RerankerModelInfo(BaseModel):
    """重排序模型信息"""
    model_id: str
    modality: List[str] = ["Text"]  # 支持的模态类型，默认为文本
    
    def get_modality_classes(self) -> List[type]:
        """获取模态类型类列表"""
        return [MODALITY_MAP.get(m, Text) for m in self.modality]


# 模型类型配置：定义每种模型的字段名、Info 类、加载方法
MODEL_TYPE_CONFIGS = {
    ModelType.LLM: {
        "field": "models",
        "info_class": ModelInfo,
        "loader_method": "load_model",
    },
    ModelType.EMBEDDING: {
        "field": "embedding_models",
        "info_class": EmbeddingModelInfo,
        "loader_method": "load_embedding_model",
    },
    ModelType.RERANKER: {
        "field": "reranker_models",
        "info_class": RerankerModelInfo,
        "loader_method": "load_reranker_model",
    },
}


class ProviderModelInfo(BaseModel):
    """
    提供商模型配置
    
    支持多种模型类型，通过统一的字段配置进行扩展
    """
    provider_type: str
    provider_name: str
    base_url: str
    models: Dict[str, ModelInfo] = {}  # LLM 模型
    embedding_models: Optional[Dict[str, EmbeddingModelInfo]] = None
    reranker_models: Optional[Dict[str, RerankerModelInfo]] = None
    
    def get_models_by_type(self, model_type: str) -> Dict:
        """根据模型类型获取对应的模型字典"""
        config = MODEL_TYPE_CONFIGS.get(model_type)
        if not config:
            return {}
        return getattr(self, config["field"], None) or {}


# 配置文件目录
PROVIDER_MODEL_INFOS_DIR = PATH_CONFIG.PROVIDER_INFOS_PATH


def _load_provider_config(file_path: Path) -> ProviderModelInfo:
    """加载单个提供商配置文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return ProviderModelInfo.model_validate_json(f.read())


def get_all_providers() -> List[ProviderModelInfo]:
    """获取所有提供商配置"""
    providers = []
    if not PROVIDER_MODEL_INFOS_DIR.exists():
        return providers
    
    for file_path in PROVIDER_MODEL_INFOS_DIR.glob("*.json"):
        try:
            provider_info = _load_provider_config(file_path)
            providers.append(provider_info)
        except Exception as e:
            print(f"Error loading provider config {file_path}: {e}")
    return providers


def _get_all_models_by_field(field_name: str) -> Dict[str, tuple]:
    """
    通用函数：根据字段名获取所有模型
    
    Args:
        field_name: ProviderModelInfo 中的字段名（如 'models', 'embedding_models'）
        
    返回：{model_name: (provider_name, model_info)}
    """
    all_models = {}
    for provider_info in get_all_providers():
        models_dict = getattr(provider_info, field_name, None)
        if models_dict:
            for model_name, model_info in models_dict.items():
                all_models[model_name] = (provider_info.provider_name, model_info)
    return all_models

def get_all_models() -> Dict[str, dict]:
    """
    获取所有类型的所有模型
    
    返回：{provider_name: {model_name: (provider_name, model_info, model_type)}}
    """
    if not MODEL_TYPE_CONFIGS:
        return {}
    
    model_infos = {}
    for model_type, type_config in MODEL_TYPE_CONFIGS.items():
        models = _get_all_models_by_field(type_config["field"])
        
        for name, model in models.items():
            provider_name, model_info = model
            
            # 初始化该提供商的字典（如果不存在）
            if provider_name not in model_infos:
                model_infos[provider_name] = {}
            
            # 添加模型信息，包含model_type
            model_infos[provider_name][name] = (provider_name, model_info, model_type)
    
    return model_infos

def get_provider_info(provider_name: str) -> Optional[ProviderModelInfo]:
    """获取提供商完整信息"""
    for provider_info in get_all_providers():
        if provider_info.provider_name == provider_name:
            return provider_info
    return None


def get_model_info(model_name: str) -> Optional[ModelInfo]:
    """获取模型信息（大小写不敏感）"""
    all_models = get_all_models()
    model_name_lower = model_name.lower()
    for provider_models in all_models.values():
        # 首先尝试精确匹配
        if model_name in provider_models:
            return provider_models[model_name][1]
        # 如果精确匹配失败，尝试大小写不敏感匹配
        for name in provider_models:
            if name.lower() == model_name_lower:
                return provider_models[name][1]
    return None
