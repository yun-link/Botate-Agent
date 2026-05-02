from typing import List, Optional, ClassVar, Literal
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class FolderPermission:

    path: str
    access_mode: Literal["read_only", "read_write", "denied"] = "read_write"


@dataclass
class PermissionConfig:
    mode: Literal["blacklist", "whitelist"] = "blacklist"
    folders: List[FolderPermission] = field(default_factory=list)
    not_allowed_commands: List[str] = field(default_factory=lambda: [
        'del', 'rd', 'format', 'reg', 'rm'
    ])


@dataclass
class ModelConfig:
    model_name: str


@dataclass
class EmbeddingModelConfig(ModelConfig):
    pass


@dataclass
class RerankerModelConfig(ModelConfig):
    pass


@dataclass
class ModelRouterConfig:
    model_names: List[str]
    router_strategies: str


@dataclass
class PathConfig:
    PROJECT_PATH: Path = field(default_factory=lambda: Path(__file__).parent.parent)
<<<<<<< HEAD
=======
    WORKSPACE_PATH: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / 'workspace')
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d

    def __post_init__(self):
        self.PROJECT_PATH = Path(self.PROJECT_PATH)
        
<<<<<<< HEAD
        self.HOME_PATH: Path = Path.home()
        self.USER_PATH: Path = self.HOME_PATH / '.botate' / 'agent'
        self.USER_PATH.mkdir(exist_ok=True, parents=True)
        self.CONFIG_PATH: Path = self.PROJECT_PATH / 'config'
        self.MCP_SERVERS_PATH: Path = self.CONFIG_PATH / 'mcp_servers.json'
        self.PROVIDER_INFOS_PATH: Path = self.CONFIG_PATH / 'provider_infos'
        self.LOGS_PATH: Path = self.USER_PATH / 'logs'
        self.WORKSPACE_PATH = self.USER_PATH / 'workspace'
        self.WORKSPACE_PATH.mkdir(exist_ok=True)
        self.ASSETS_PATH: Path = self.PROJECT_PATH / 'assets'
        self.SKILL_PATH: Path = self.ASSETS_PATH / 'skills'
        self.PROMPTS_PATH: Path = self.ASSETS_PATH / 'prompts'
        self.MEMORYBANK_PATH: Path = self.USER_PATH / 'memory'
=======
        self.WORKSPACE_PATH = Path(self.WORKSPACE_PATH)
        self.WORKSPACE_PATH.mkdir(exist_ok=True)
        
        self.CONFIG_PATH: Path = self.PROJECT_PATH / 'config'
        self.MCP_SERVERS_PATH: Path = self.CONFIG_PATH / 'mcp_servers.json'
        self.PROVIDER_INFOS_PATH: Path = self.CONFIG_PATH / 'provider_infos'
        self.LOGS_PATH: Path = self.PROJECT_PATH / 'logs'

        self.ASSETS_PATH: Path = self.PROJECT_PATH / 'assets'
        self.SKILL_PATH: Path = self.ASSETS_PATH / 'skills'
        self.PROMPTS_PATH: Path = self.ASSETS_PATH / 'prompts'
        self.MEMORYBANK_PATH: Path = self.ASSETS_PATH / 'memory_bank'
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d


@dataclass
class AgentConfig:
    WOKRER_AGENT_MODEL: ModelConfig | ModelRouterConfig = field(default_factory=lambda: ModelConfig(model_name='doubao-seed-2.0-lite'))
<<<<<<< HEAD
    CONTEXT_MANAGER_MODEL: ModelConfig = field(default_factory=lambda: ModelConfig(model_name='doubao-seed-2.0-mini'))
=======
    CONTEXT_MANAGER_MODEL: ModelConfig = field(default_factory=lambda: ModelConfig(model_name='doubao-seed-1.8'))
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d

    MEMORY_SAVE_INTERVAL_HOURS: int = 1


@dataclass
class MemoryBankConfig:
<<<<<<< HEAD
    RERANKER_MODEL: RerankerModelConfig = field(default_factory=lambda: RerankerModelConfig(model_name='qwen3-reranker-8b'))
    SUMMARY_MODEL: ModelConfig = field(default_factory=lambda: ModelConfig(model_name='doubao-seed-2.0-mini'))

    ENABLE_GENERATE_SUMMARY: bool = True
=======
    EMBEDDING_MODEL: EmbeddingModelConfig = field(default_factory=lambda: EmbeddingModelConfig(model_name='qwen3-embedding-8b'))
    RERANKER_MODEL: RerankerModelConfig = field(default_factory=lambda: RerankerModelConfig(model_name='qwen3-reranker-8b'))
    SUMMARY_MODEL: ModelConfig = field(default_factory=lambda: ModelConfig(model_name='doubao-seed-1.6-lite'))

    ENABLE_GENERATE_SUMMARY: bool = True
    ENABLE_GENERATE_VECTOR: bool = True
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
    ENABLE_RERANK: bool = True

    UPDATE_RATE: int = 72
    UPADATE_DECAY_WEIGHT: float = 0.05
    FORGET_THRESHOLD_WEIGHT: float = 0.1
    IMPROTANT_WEIGHT: float = -1


def load_path_config() -> PathConfig:
    """Return PathConfig instance with default values."""
    return PathConfig()


def load_agent_config() -> AgentConfig:
    """Return AgentConfig instance with default values."""
    return AgentConfig()


def load_memory_bank_config() -> MemoryBankConfig:
    """Return MemoryBankConfig instance with default values."""
    return MemoryBankConfig()

def load_permission_config() -> PermissionConfig:

    return PermissionConfig()
