from .model import (
    Model, 
    ModelConfig, 
    get_model_info, 
    call, 
    call_async,
    EmbeddingModel,
    embed,
    embed_async,
    list_all_embedding_models,
    RerankerModel,
    rerank,
    rerank_async,
    list_all_reranker_models
)
from .message_schemas.message_schemas import (
    Message,
    Text,
    Image,
    Audio,
    Video,
    ReasoningContent,
    ResponseContent,
    FunctionCallContent,
    AnswerContent
)
from .model_router import (
    ModelRouter, 
    ModelRouterConfig,
    effectiveness_first,
    cost_first,
    balance,
    call as router_call,
    call_async as router_call_async
)

from .tool import (
    Tool,
    ToolParameters,
    ToolSchema,
    MCPConfig,
    MCPClient,
    MCPServerConfig,
    MCPTool
)


__all__ = [
    'Model',
    'ModelConfig',
    'get_model_info',
    'call',
    'call_async',
    'Message',
    'Text',
    'Image',
    'Audio',
    'Video',
    'ReasoningContent',
    'ResponseContent',
    'FunctionCallContent',
    'AnswerContent',
    'ModelRouter',
    'ModelRouterConfig',
    'effectiveness_first',
    'cost_first',
    'balance',
    'router_call',
    'router_call_async',
    'load_model_from_config',
    # Tool
    'Tool',
    'ToolParameters',
    'ToolSchema',
    'MCPConfig',
    'MCPClient',
    'MCPServerConfig',
    'MCPTool',
    # Embedding
    'EmbeddingModel',
    'embed',
    'embed_async',
    'list_all_embedding_models',
    # Reranker
    'RerankerModel',
    'rerank',
    'rerank_async',
    'list_all_reranker_models',
]


def load_model_from_config(config, *args, **kwargs):
    if isinstance(config, ModelConfig):
        return Model.from_model_config(config, *args, **kwargs)
    else:
        return ModelRouter.from_model_router_config(config, *args, **kwargs)
