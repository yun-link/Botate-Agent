"""
MCP 客户端模块 (使用官方 mcp 库)

基于官方 Model Context Protocol Python SDK 实现，支持与 MCP 服务器通信。
"""

import json
import asyncio
import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent, ImageContent, EmbeddedResource

from .mcp_config import MCPConfig, MCPServerConfig
from ..tool_schema import Tool, register_tool


class TransportType(str, Enum):
    """传输类型枚举"""
    STDIO = "stdio"
    SSE = "sse"  # Server-Sent Events (HTTP)
    STREAMABLE_HTTP = "streamable_http"  # Streamable HTTP (MCP 官方推荐)


class MCPError(Exception):
    """MCP 相关异常"""
    def __init__(self, message: str, code: Optional[int] = None):
        self.message = message
        self.code = code
        super().__init__(f"[MCP Error {code}] {message}" if code else message)


def _run_async(coro):
    """
    在独立线程中运行异步协程
    
    避免嵌套事件循环问题，确保在任何环境下都能安全执行异步操作。
    """
    result = None
    exception = None
    
    def run_in_thread():
        nonlocal result, exception
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
        except Exception as e:
            exception = e
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    
    if exception is not None:
        raise exception
    return result


class MCPClient:
    """
    MCP 客户端 (基于官方 mcp 库)
    
    支持与 MCP 服务器进行 STDIO 或 SSE 通信，发送工具调用请求。
    """
    
    def __init__(
        self,
        config: Optional[MCPConfig] = None,
        server_name: Optional[str] = None
    ):
        """
        初始化 MCP 客户端
        
        Args:
            config: MCP 配置，如果为 None 则自动加载
            server_name: 默认服务器名称
        """
        self.config = config or MCPConfig.load()
        self.server_name = server_name or self.config.default_server
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._streamable_http_cm = None
    
    def _get_server_config(self, name: Optional[str] = None) -> MCPServerConfig:
        """获取服务器配置"""
        server = self.config.get_server(name or self.server_name)
        if not server:
            raise MCPError(f"服务器配置不存在：{name or self.server_name}")
        return server
    
    def _create_server_params(self, server_config: MCPServerConfig) -> StdioServerParameters:
        """创建 STDIO 服务器参数"""
        if server_config.command:
            command = server_config.command
            args = server_config.args or []
        else:
            endpoint = server_config.endpoint
            if endpoint.endswith('.py'):
                command = "python"
                args = [endpoint]
            elif endpoint.endswith('.js'):
                command = "node"
                args = [endpoint]
            elif endpoint.endswith('.sh'):
                command = "bash"
                args = [endpoint]
            else:
                raise MCPError(f"无法推断服务器命令，请配置 command 和 args: {endpoint}")
        
        return StdioServerParameters(
            command=command,
            args=args,
            env=server_config.env
        )
    
    async def connect(self, server_name: Optional[str] = None) -> None:
        """
        连接到 MCP 服务器（异步）
        
        Args:
            server_name: 服务器名称，默认使用初始化时指定的服务器
        """
        server_config = self._get_server_config(server_name)
        
        if self._exit_stack is None:
            self._exit_stack = AsyncExitStack()
        
        transport = server_config.transport.lower()
        
        try:
            if transport == TransportType.STDIO.value:
                server_params = self._create_server_params(server_config)
                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                self._session = await self._exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                
            elif transport == TransportType.SSE.value:
                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    sse_client(url=server_config.endpoint, headers=server_config.headers)
                )
                self._session = await self._exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                
            elif transport == TransportType.STREAMABLE_HTTP.value:
                self._streamable_http_cm = streamablehttp_client(url=server_config.endpoint, headers=server_config.headers)
                read_stream, write_stream, _ = await self._streamable_http_cm.__aenter__()
                self._session = await self._exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                
            else:
                raise MCPError(f"不支持的传输类型：{transport}")
            
            await self._session.initialize()
            
        except Exception as e:
            await self.disconnect()
            raise MCPError(f"连接服务器失败：{str(e)}")
    
    async def disconnect(self) -> None:
        """断开与 MCP 服务器的连接"""
        if self._session:
            self._session = None
        
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
        
        if self._streamable_http_cm:
            try:
                await self._streamable_http_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._streamable_http_cm = None
    
    def _ensure_connected(self) -> ClientSession:
        """确保已连接到服务器"""
        if self._session is None:
            raise MCPError("未连接到 MCP 服务器，请先调用 connect()")
        return self._session
    
    async def list_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出远程服务器上的所有工具
        
        Args:
            server_name: 服务器名称（已连接的服务器，此参数仅用于兼容性）
            
        Returns:
            工具列表
        """
        session = self._ensure_connected()
        result = await session.list_tools()
        
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema
            }
            for tool in result.tools
        ]
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: Optional[str] = None
    ) -> Any:
        """
        调用远程 MCP 工具（异步）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            server_name: 服务器名称（已连接的服务器，此参数仅用于兼容性）
            
        Returns:
            工具执行结果
        """
        session = self._ensure_connected()
        result = await session.call_tool(tool_name, arguments)
        
        contents = []
        for content in result.content:
            if isinstance(content, TextContent):
                contents.append(content.text)
            elif isinstance(content, ImageContent):
                contents.append({
                    "type": "image",
                    "data": content.data,
                    "mimeType": content.mimeType
                })
            elif isinstance(content, EmbeddedResource):
                contents.append({
                    "type": "resource",
                    "resource": content.resource
                })
        
        return contents[0] if len(contents) == 1 else contents
    
    async def list_resources(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出可用资源
        
        Args:
            server_name: 服务器名称
            
        Returns:
            资源列表
        """
        session = self._ensure_connected()
        result = await session.list_resources()
        
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mimeType
            }
            for resource in result.resources
        ]
    
    async def read_resource(self, uri: str) -> Any:
        """
        读取资源内容
        
        Args:
            uri: 资源 URI
            
        Returns:
            资源内容
        """
        session = self._ensure_connected()
        return await session.read_resource(uri)
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        获取提示词模板
        
        Args:
            name: 提示词名称
            arguments: 提示词参数
            
        Returns:
            提示词内容
        """
        session = self._ensure_connected()
        return await session.get_prompt(name, arguments or {})
    
    # 同步包装方法
    def call_tool_sync(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: Optional[str] = None
    ) -> Any:
        """同步调用远程 MCP 工具"""
        async def _call():
            await self.connect(server_name)
            try:
                return await self.call_tool(tool_name, arguments, server_name)
            finally:
                await self.disconnect()
        return _run_async(_call())
    
    def list_tools_sync(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """同步列出工具"""
        async def _list():
            await self.connect(server_name)
            try:
                return await self.list_tools(server_name)
            finally:
                await self.disconnect()
        return _run_async(_list())
    
    def get_tool_schema(
        self,
        tool_name: str,
        server_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取远程工具的 Schema"""
        tools = self.list_tools_sync(server_name)
        for tool in tools:
            if tool.get("name") == tool_name:
                return tool
        return None
    
    # 异步上下文管理器
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


def create_mcp_client(
    config: Optional[MCPConfig] = None,
    server_name: Optional[str] = None
) -> MCPClient:
    """创建 MCP 客户端的便捷函数"""
    return MCPClient(config=config, server_name=server_name)


class MCPTool(Tool):
    """
    MCP 工具类，继承自 Tool
    
    封装 MCP 远程工具调用，通过 MCP 客户端执行远程工具。
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        mcp_client: MCPClient,
        parameters: Optional[Dict[str, Any]] = None,
        server_name: Optional[str] = None
    ):
        """
        初始化 MCP 工具
        
        Args:
            name: 工具名称
            description: 工具描述
            mcp_client: MCP 客户端实例
            parameters: 参数定义（JSON Schema 格式）
            server_name: 目标服务器名称
        """
        self.mcp_client = mcp_client
        self.server_name = server_name
        
        def handler(params: Dict[str, Any]) -> Any:
            return mcp_client.call_tool_sync(
                tool_name=name,
                arguments=params,
                server_name=server_name
            )
        
        super().__init__(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters
        )
    
    @classmethod
    def from_tool_info(
        cls,
        tool_info: Dict[str, Any],
        mcp_client: MCPClient,
        server_name: Optional[str] = None
    ) -> "MCPTool":
        """从工具信息字典创建 MCPTool"""
        name = tool_info.get("name", "")
        description = tool_info.get("description", "")
        input_schema = tool_info.get("inputSchema", {})
        
        parameters = {
            "type": input_schema.get("type", "object"),
            "properties": input_schema.get("properties", {}),
            "required": input_schema.get("required", []),
            "additionalProperties": input_schema.get("additionalProperties", False)
        }
        
        return cls(
            name=name,
            description=description,
            mcp_client=mcp_client,
            parameters=parameters,
            server_name=server_name
        )


async def _load_tools_from_server(
    mcp_config: MCPConfig,
    server_name: str,
    tool_names: Optional[List[str]] = None,
    auto_register: bool = True
) -> List[MCPTool]:
    """
    从单个 MCP 服务器加载工具（内部异步函数）
    
    Args:
        mcp_config: MCP 配置
        server_name: 服务器名称
        tool_names: 要加载的工具名称列表，为 None 则加载所有
        auto_register: 是否自动注册到全局工具表
        
    Returns:
        MCPTool 实例列表
    """
    mcp_tools = []
    
    async with MCPClient(config=mcp_config, server_name=server_name) as client:
        remote_tools = await client.list_tools()
        
        for tool_info in remote_tools:
            tool_name = tool_info.get("name", "")
            
            if tool_names is not None and tool_name not in tool_names:
                continue
            
            mcp_tool = MCPTool.from_tool_info(
                tool_info=tool_info,
                mcp_client=client,
                server_name=server_name
            )
            mcp_tools.append(mcp_tool)
            
            if auto_register:
                register_tool(mcp_tool)
    
    return mcp_tools


def load_mcp_tools_from_mcpservers_config(
    config_path: Path,
    tool_names: Optional[Dict[str, List[str]]] = None,
    auto_register: bool = True
) -> List[MCPTool]:
    """
    从 Claude Desktop 格式的 JSON 配置文件加载 MCP 工具
    
    支持完整的 Claude Desktop 配置格式，所有认证信息通过 headers 配置。
    
    配置文件格式示例（Claude Desktop 格式）：
    {
        "mcpServers": {
            "http-server": {
                "url": "https://mcp.api-inference.modelscope.net/114e2047bd6a49/mcp",
                "type": "streamable_http",
                "headers": {
                    "Authorization": "Bearer your-api-key",
                    "X-Custom-Header": "value"
                },
                "timeout": 60
            },
            "sse-server": {
                "url": "https://another-server.com/mcp",
                "type": "sse",
                "headers": {}
            },
            "stdio-server": {
                "command": "python",
                "args": ["-m", "mcp_server_weather"],
                "env": {
                    "API_KEY": "xxx"
                }
            }
        }
    }
    
    Args:
        config_path: 配置文件路径
        tool_names: 可选的字典，指定每个服务器要加载的工具列表
        auto_register: 是否自动注册到全局工具表
        
    Returns:
        MCPTool 实例列表
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    mcp_servers = config_data.get("mcpServers", {})
    if not mcp_servers:
        raise MCPError("配置文件中未找到 mcpServers")
    
    async def _load_all():
        all_tools = []
        for server_name, server_config in mcp_servers.items():
            # 获取端点（支持 url 或 endpoint 字段）
            endpoint = server_config.get("url") or server_config.get("endpoint", "")
            
            # 获取传输类型（默认为 streamable_http）
            transport = server_config.get("type", "streamable_http")
            
            # 检查是否是 stdio 传输（有 command 字段）
            command = server_config.get("command")
            
            if command:
                # stdio 传输模式
                args = server_config.get("args", [])
                env = server_config.get("env", {})
                
                # 构建端点标识符
                if not endpoint:
                    endpoint = f"{command} {' '.join(args)}" if args else command
                
                mcpserver_config = MCPServerConfig(
                    name=server_name,
                    endpoint=endpoint,
                    command=command,
                    args=args,
                    env=env,
                    transport="stdio",
                    timeout=server_config.get("timeout", 30),
                    headers=server_config.get("headers", {})
                )
            elif endpoint:
                # HTTP/SSE 传输模式
                mcpserver_config = MCPServerConfig(
                    name=server_name,
                    endpoint=endpoint,
                    transport=transport,
                    timeout=server_config.get("timeout", 30),
                    headers=server_config.get("headers", {})
                )
            else:
                print(f"警告：服务器 {server_name} 未配置 url/endpoint 或 command，跳过")
                continue
            
            mcp_config = MCPConfig(
                default_server=server_name,
                servers={server_name: mcpserver_config}
            )
            
            server_tool_names = tool_names.get(server_name) if tool_names else None
            tools = await _load_tools_from_server(
                mcp_config=mcp_config,
                server_name=server_name,
                tool_names=server_tool_names,
                auto_register=auto_register
            )
            all_tools.extend(tools)
        return all_tools
    
    return _run_async(_load_all())
