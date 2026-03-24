"""
MCP 配置模块

提供 MCP 客户端的配置定义，支持从环境变量或 JSON 文件加载配置。
"""

import os
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field


# 默认配置文件路径（相对于当前模块）
DEFAULT_CONFIG_FILE = Path(__file__).parent / "mcp_config.json"


class MCPServerConfig(BaseModel):
    """单个 MCP 服务器的配置
    
    支持 Claude Desktop 格式配置：
    - url: 服务器 URL（HTTP/SSE 传输）
    - command: 命令（stdio 传输）
    - args: 命令参数
    - env: 环境变量
    - type: 传输类型 (stdio, sse, streamable_http)
    - headers: 请求头（包含认证信息等）
    - timeout: 超时时间
    """
    name: str = Field(..., description="服务器名称")
    endpoint: str = Field(default="", description="MCP 服务器端点 URL")
    command: Optional[str] = Field(default=None, description="stdio 传输的命令")
    args: List[str] = Field(default_factory=list, description="命令参数")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    transport: str = Field(default="streamable_http", description="传输协议 (stdio, sse, streamable_http)")
    timeout: int = Field(default=30, description="请求超时时间（秒）")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头（包含认证信息等）")
    
    class Config:
        extra = "allow"


class MCPConfig(BaseModel):
    """
    MCP 客户端配置
    
    配置加载优先级：
    1. 环境变量
    2. JSON 配置文件
    3. 默认值
    """
    # 默认服务器配置
    default_server: Optional[str] = Field(
        default=None, 
        description="默认 MCP 服务器名称"
    )
    
    # 服务器列表
    servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict,
        description="MCP 服务器配置列表"
    )
    
    # 全局设置
    global_timeout: int = Field(
        default=60,
        description="全局默认超时时间（秒）"
    )
    
    retry_attempts: int = Field(
        default=3,
        description="重试次数"
    )
    
    retry_delay: float = Field(
        default=1.0,
        description="重试间隔（秒）"
    )
    
    enable_logging: bool = Field(
        default=True,
        description="是否启用日志记录"
    )
    
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    @classmethod
    def from_env(cls) -> "MCPConfig":
        """
        从环境变量加载配置
        
        支持的环境变量：
        - MCP_DEFAULT_SERVER: 默认服务器名称
        - MCP_ENDPOINT: 默认服务器端点
        - MCP_TIMEOUT: 默认超时时间
        - MCP_SERVERS_JSON: JSON 格式的服务器配置
        - MCP_HEADERS_JSON: JSON 格式的请求头
        
        Returns:
            MCPConfig 实例
        """
        config_data = {}
        
        # 读取基本配置
        if os.getenv("MCP_DEFAULT_SERVER"):
            config_data["default_server"] = os.getenv("MCP_DEFAULT_SERVER")
        
        if os.getenv("MCP_TIMEOUT"):
            try:
                config_data["global_timeout"] = int(os.getenv("MCP_TIMEOUT"))
            except ValueError:
                pass
        
        if os.getenv("MCP_RETRY_ATTEMPTS"):
            try:
                config_data["retry_attempts"] = int(os.getenv("MCP_RETRY_ATTEMPTS"))
            except ValueError:
                pass
        
        if os.getenv("MCP_RETRY_DELAY"):
            try:
                config_data["retry_delay"] = float(os.getenv("MCP_RETRY_DELAY"))
            except ValueError:
                pass
        
        if os.getenv("MCP_ENABLE_LOGGING"):
            config_data["enable_logging"] = os.getenv("MCP_ENABLE_LOGGING").lower() == "true"
        
        if os.getenv("MCP_LOG_LEVEL"):
            config_data["log_level"] = os.getenv("MCP_LOG_LEVEL")
        
        # 读取默认服务器配置
        endpoint = os.getenv("MCP_ENDPOINT")
        
        if endpoint:
            server_name = os.getenv("MCP_SERVER_NAME", "default")
            
            # 从环境变量构建 headers
            headers = {}
            headers_json = os.getenv("MCP_HEADERS_JSON")
            if headers_json:
                try:
                    headers = json.loads(headers_json)
                except json.JSONDecodeError:
                    pass
            
            config_data["servers"] = {
                server_name: {
                    "name": server_name,
                    "endpoint": endpoint,
                    "transport": os.getenv("MCP_TRANSPORT", "streamable_http"),
                    "timeout": int(os.getenv("MCP_TIMEOUT", "30")) if os.getenv("MCP_TIMEOUT") else 30,
                    "headers": headers
                }
            }
            if not config_data.get("default_server"):
                config_data["default_server"] = server_name
        
        # 读取多个服务器配置（JSON 格式）
        servers_json = os.getenv("MCP_SERVERS_JSON")
        if servers_json:
            try:
                servers_data = json.loads(servers_json)
                for name, server_config in servers_data.items():
                    if "name" not in server_config:
                        server_config["name"] = name
                    config_data.setdefault("servers", {})[name] = server_config
            except json.JSONDecodeError as e:
                print(f"警告：解析 MCP_SERVERS_JSON 失败：{e}")
        
        return cls(**config_data)
    
    @classmethod
    def from_file(cls, config_path: Optional[Path] = None) -> "MCPConfig":
        """
        从 JSON 文件加载配置
        
        Args:
            config_path: 配置文件路径，默认为 mcp_config.json
            
        Returns:
            MCPConfig 实例
        """
        if isinstance(config_path, str):
            config_path = Path(config_path) 
        if config_path is None:
            config_path = DEFAULT_CONFIG_FILE
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        return cls(**config_data)
    
    @classmethod
    def load(
        cls, 
        config_path: Optional[Path] = None,
        prefer_env: bool = True
    ) -> "MCPConfig":
        """
        加载配置（优先从环境变量，否则从文件）
        
        Args:
            config_path: 配置文件路径
            prefer_env: 是否优先使用环境变量
            
        Returns:
            MCPConfig 实例
        """
        if prefer_env and cls._has_env_config():
            return cls.from_env()
        
        try:
            return cls.from_file(config_path)
        except FileNotFoundError:
            # 如果文件不存在且没有环境变量配置，返回默认配置
            if not cls._has_env_config():
                return cls()
            return cls.from_env()
    
    @classmethod
    def _has_env_config(cls) -> bool:
        """检查是否存在环境变量配置"""
        return bool(
            os.getenv("MCP_ENDPOINT") or 
            os.getenv("MCP_SERVERS_JSON") or
            os.getenv("MCP_DEFAULT_SERVER")
        )
    
    def get_server(self, name: Optional[str] = None) -> Optional[MCPServerConfig]:
        """
        获取指定服务器配置
        
        Args:
            name: 服务器名称，如果为 None 则返回默认服务器
            
        Returns:
            服务器配置，如果不存在则返回 None
        """
        if name is None:
            name = self.default_server
        
        if name is None:
            # 返回第一个服务器
            if self.servers:
                return next(iter(self.servers.values()))
            return None
        
        return self.servers.get(name)
    
    def get_server_endpoint(self, name: Optional[str] = None) -> Optional[str]:
        """获取服务器端点"""
        server = self.get_server(name)
        return server.endpoint if server else None
    
    def add_server(self, config: MCPServerConfig) -> None:
        """添加服务器配置"""
        self.servers[config.name] = config
    
    def remove_server(self, name: str) -> bool:
        """移除服务器配置"""
        if name in self.servers:
            del self.servers[name]
            if self.default_server == name:
                self.default_server = None
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save_to_file(self, config_path: Path) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 保存路径
        """
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())


def get_mcp_config(
    config_path: Optional[Path] = None,
    prefer_env: bool = True
) -> MCPConfig:
    """
    获取 MCP 配置的便捷函数
    
    Args:
        config_path: 配置文件路径
        prefer_env: 是否优先使用环境变量
        
    Returns:
        MCPConfig 实例
    """
    return MCPConfig.load(config_path, prefer_env)
