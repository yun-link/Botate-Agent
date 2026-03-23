"""
记忆库工具模块

提供记忆搜索功能。
"""

from typing import List
from model.tool import Tool
from ..memory_bank.memory_bank import get_memory_bank


def _search_memory_handler(params: dict) -> str:
    """
    记忆搜索处理函数
    
    Args:
        params: 包含以下键的字典：
            - query: 搜索关键词
            - top_k: 返回结果数量（可选，默认10）
            - depth: 搜索深度（可选，默认0）
            
    Returns:
        搜索结果信息
    """
    query = params.get("query")
    top_k = params.get("top_k", 10)
    depth = params.get("depth", 0)
    
    if not query:
        return "错误：未提供搜索关键词"
    
    # 获取记忆库实例
    memory_bank = get_memory_bank()
    if memory_bank is None:
        return "错误：记忆库未初始化，请先调用 load_memory_bank 初始化记忆库"
    
    try:
        # 执行搜索
        results = memory_bank.search(
            query=query,
            top_k=top_k,
            depth=depth
        )
        
        if not results:
            return "未找到相关记忆"
        
        # 格式化输出结果
        output_lines = []
        for i, result in enumerate(results, 1):
            memory = result.memory
            score = result.score
            
            output_lines.append(f"[记忆 {i}] (相关度: {score:.2f})")
            output_lines.append(f"ID: {memory.id}")
            if memory.summary:
                output_lines.append(f"摘要: {memory.summary}")
            output_lines.append(f"内容: {memory.text_content}")
            output_lines.append(f"权重: {memory.weight}")
            output_lines.append(f"创建时间: {memory.created_at}")
            output_lines.append("")
        
        return "\n".join(output_lines)
    except Exception as e:
        return f"错误：搜索记忆时发生异常 - {str(e)}"


# 定义 SearchMemory 工具
SearchMemory = Tool(
    name="SearchMemory",
    description="搜索记忆库工具。在记忆库中搜索与关键词相关的记忆，返回匹配的记忆内容、摘要、权重等信息。支持设置搜索深度来扩展搜索关联记忆。",
    handler=_search_memory_handler,
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词或查询内容"
            },
            "top_k": {
                "type": "integer",
                "description": "返回结果数量，默认为10",
                "default": 10
            },
            "depth": {
                "type": "integer",
                "description": "搜索深度：0表示只检索关键词匹配的记忆，1表示继续检索匹配记忆的关联记忆。默认为0",
                "default": 0
            }
        },
        "required": ["query"]
    }
)
