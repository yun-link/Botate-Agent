"""
工具模块

提供全局工具加载和管理功能。
"""

from typing import List
from model.tool import Tool
from model.tool.mcp import load_mcp_tools_from_mcpservers_config
from config import PATH_CONFIG

from .basic_tools import StrReplace, WriteFile, ReadFile, ListFiles, SearchFiles, RunCommand
from .search import WebSearch
from .memory_bank import SearchMemory


def load_global_tools() -> List[Tool]:

    mcp_tools = []
    try:
        mcp_tools = load_mcp_tools_from_mcpservers_config(PATH_CONFIG.MCP_SERVERS_PATH)
    except Exception:
        pass
    return [
        StrReplace, 
        WriteFile, 
        ReadFile, 
        ListFiles, 
        SearchFiles, 
        WebSearch, 
        SearchMemory,
        RunCommand
    ] + mcp_tools
