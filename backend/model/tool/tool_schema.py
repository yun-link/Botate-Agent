"""
工具调用 Schema 定义模块

提供符合 OpenAI 标准的工具 Schema 定义，以及工具注册和管理功能。
"""

from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, Field
import json


# 全局工具注册表
_registered_tools: Dict[str, "Tool"] = {}


class ToolParameters(BaseModel):
    """工具参数的 JSON Schema 定义"""
    type: str = Field(default="object", description="参数类型，固定为 object")
    properties: Dict[str, Any] = Field(default_factory=dict, description="参数属性定义")
    required: List[str] = Field(default_factory=list, description="必需的参数列表")
    additionalProperties: bool = Field(default=False, description="是否允许额外属性")


class ToolSchema(BaseModel):
    """
    符合 OpenAI 标准的工具 Schema 定义
    """
    type: str = Field(default="function", description="工具类型，固定为 function")
    function: Dict[str, Any] = Field(..., description="函数定义")
    
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> "ToolSchema":
        """
        创建工具 Schema
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 参数定义（JSON Schema 格式）
            
        Returns:
            ToolSchema 实例
        """
        if parameters is None:
            parameters = {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        
        return cls(
            type="function",
            function={
                "name": name,
                "description": description,
                "parameters": parameters
            }
        )
    
    @property
    def name(self) -> str:
        """获取工具名称"""
        return self.function.get("name", "")
    
    @property
    def description(self) -> str:
        """获取工具描述"""
        return self.function.get("description", "")
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """获取参数定义"""
        return self.function.get("parameters", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.model_dump()
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为 OpenAI API 格式"""
        return self.to_dict()


class Tool:
    """
    工具类，封装工具的定义和执行逻辑
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[[Dict[str, Any]], Any],
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
            handler: 执行函数，接受 params 字典参数
            parameters: 参数定义（JSON Schema 格式）
        """
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters or {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    
    @property
    def schema(self) -> ToolSchema:
        """获取工具的 Schema"""
        return ToolSchema.create(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )
    
    def execute(self, params: Dict[str, Any]) -> Any:
        """
        执行工具
        
        Args:
            params: 参数字典
            
        Returns:
            执行结果
        """
        return self.handler(params)
    
    def __call__(self, params: Dict[str, Any]) -> Any:
        """允许直接调用工具"""
        return self.execute(params)

    def __str__(self) -> str:
        return f"Tool(name='{self.name}', description='{self.description}', parameters={self.parameters})"
    def __repr__(self):
        return self.__str__()

def register_tool(tool: Tool) -> None:
    """
    注册工具到全局字典
    
    Args:
        tool: 要注册的工具实例
    """
    _registered_tools[tool.name] = tool


def register_tool_by_name(
    name: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    装饰器方式注册工具
    
    Args:
        name: 工具名称
        description: 工具描述
        parameters: 参数定义（JSON Schema 格式）
        
    Returns:
        装饰器函数
    """
    def decorator(handler: Callable[[Dict[str, Any]], Any]) -> Callable:
        tool = Tool(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters
        )
        register_tool(tool)
        return handler
    return decorator


def get_tool(name: str) -> Optional[Tool]:
    """
    获取已注册的工具
    
    Args:
        name: 工具名称
        
    Returns:
        工具实例，如果不存在则返回 None
    """
    return _registered_tools.get(name)


def get_all_tools() -> Dict[str, Tool]:
    """
    获取所有已注册的工具
    
    Returns:
        工具字典
    """
    return _registered_tools.copy()


def list_tool_names() -> List[str]:
    """
    获取所有已注册工具的命名列表
    
    Returns:
        工具名称列表
    """
    return list(_registered_tools.keys())


def get_all_schemas() -> List[Dict[str, Any]]:
    """
    获取所有已注册工具的 Schema 列表（OpenAI 格式）
    
    Returns:
        Schema 列表
    """
    return [tool.schema.to_openai_format() for tool in _registered_tools.values()]


def call_tool(tool_name: str, params: Dict[str, Any]) -> Any:
    """
    调用已注册的工具（自动路由）
    
    Args:
        tool_name: 工具名称
        params: 参数字典
        
    Returns:
        执行结果
        
    Raises:
        ValueError: 如果工具未注册
    """
    tool = get_tool(tool_name)
    if tool is None:
        raise ValueError(f"工具 '{tool_name}' 未注册")
    return tool.execute(params)


def clear_tools() -> None:
    """清空所有已注册的工具"""
    _registered_tools.clear()
