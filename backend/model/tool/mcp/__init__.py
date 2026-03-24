"""
MCP 模块

提供 MCP (Model Context Protocol) 客户端的配置和通信功能。
"""

from .mcp_config import (
    MCPConfig,
    MCPServerConfig,
    get_mcp_config,
    DEFAULT_CONFIG_FILE
)

from .mcp_client import (
    MCPClient,
    MCPError,
    TransportType,
    create_mcp_client,
    MCPTool,
    load_mcp_tools_from_mcpservers_config
)

__all__ = [
    # Config
    "MCPConfig",
    "MCPServerConfig",
    "get_mcp_config",
    "DEFAULT_CONFIG_FILE",
    # Client
    "MCPClient",
    "MCPError",
    "TransportType",
    "create_mcp_client",
    # MCP Tool
    "MCPTool",
    "load_mcp_tools_from_mcpservers_config",
]
