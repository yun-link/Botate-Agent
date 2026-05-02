"""
基础工具模块

提供通用的文件操作工具，包括字符串替换、文件写入、文件读取和目录列表功能。
"""

import os
from pathlib import Path
from typing import Callable, Dict, Optional, Any
import fnmatch

import subprocess

from model.tool import Tool
from agent.events import PermissionDeniedEvent
from agent.permission import PermissionManager
from config.config import load_path_config

# 全局权限管理器实例
_permission_manager: Optional[PermissionManager] = PermissionManager()
_check_permission: bool = True

PATH_CONFIG = load_path_config()

def set_check_permission(check: bool = True):
    global _check_permission
    _check_permission = check

def _handle_permission_file(path: str, handle_f: Callable, *args, **kwargs):
    path: Path = Path(path).absolute()
    if _check_permission:
        check_result = _permission_manager.check_permission_for_file(str(path))
        if check_result.allowed:
            return handle_f(path, *args, **kwargs)
        elif not check_result.allowed:
            return check_result
    return handle_f(path, *args, **kwargs)

def _str_replace_handler(params: dict) -> str:
    """
    字符串替换处理函数
    
    Args:
        params: 包含以下键的字典：
            - path: 文件路径
            - old_str: 要替换的旧字符串
            - new_str: 新字符串内容
            
    Returns:
        操作结果信息
    """
    path = params.get("path")
    old_str = params.get("old_str")
    new_str = params.get("new_str", "")
    
    if not path:
        return "错误：未提供文件路径"
    if old_str is None:
        return "错误：未提供要替换的字符串"
    
    def _handle_function(path, old_str, new_str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_str not in content:
                return f"错误：在文件 '{path}' 中未找到要替换的字符串"
            
            new_content = content.replace(old_str, new_str, 1)  # 只替换第一个匹配
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return f"成功：已在文件 '{path}' 中替换字符串"
        except FileNotFoundError:
            return f"错误：文件 '{path}' 不存在"
        except Exception as e:
            return f"错误：替换字符串时发生异常 - {str(e)}"
    return _handle_permission_file(path, _handle_function, new_str, old_str)


def _write_file_handler(params: dict) -> str:
    """
    文件写入处理函数
    
    Args:
        params: 包含以下键的字典：
            - path: 文件路径
            - content: 要写入的内容
            
    Returns:
        操作结果信息
    """
    path = Path(params.get("path"))
    path.parent.mkdir(exist_ok=True)
    content = params.get("content", "")
    def _write_file(path, content):
        if not path:
            return "错误：未提供文件路径"
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"成功：已写入文件 '{path}'"
        except Exception as e:
            return f"错误：写入文件时发生异常 - {str(e)}"
    return _handle_permission_file(path, _write_file, content)

def _read_file_handler(params: dict) -> str:
    """
    文件读取处理函数
    
    Args:
        params: 包含以下键的字典：
            - path: 文件路径
            
    Returns:
        文件内容或错误信息
    """
    path = params.get("path")
    
    if not path:
        return "错误：未提供文件路径"
    def _read_file(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"文件内容:\n{content}"
        except FileNotFoundError:
            return f"错误：文件 '{path}' 不存在"
        except Exception as e:
            return f"错误：读取文件时发生异常 - {str(e)}"
    return _handle_permission_file(path, _read_file)


def _list_files_handler(params: dict) -> str:
    """
    目录列表处理函数
    
    Args:
        params: 包含以下键的字典：
            - path: 目录路径
            
    Returns:
        目录内容列表或错误信息
    """
    path = params.get("path")
    
    if not path:
        return "错误：未提供目录路径"
    def _list_files(path):
        try:
            items = os.listdir(path)
            result = []
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    result.append(f"[DIR] {item}")
                else:
                    result.append(f"[FILE] {item}")
            return "目录内容:\n" + "\n".join(result)
        except FileNotFoundError:
            return f"错误：目录 '{path}' 不存在"
        except NotADirectoryError:
            return f"错误：'{path}' 不是目录"
        except Exception as e:
            return f"错误：列出目录内容时发生异常 - {str(e)}"
    return _handle_permission_file(path, _list_files)

def _search_files_handler(params: dict) -> str:
    """
    文件搜索处理函数
    
    Args:
        params: 包含以下键的字典：
            - path: 搜索的根目录路径
            - pattern: 文件名匹配模式（支持通配符）
            - max_results: 最大结果数量（可选，默认 100）
            
    Returns:
        匹配的文件列表或错误信息
    """
    
    
    path = params.get("path")
    pattern = params.get("pattern", "*")
    max_results = params.get("max_results", 100)
    
    if not path:
        return "错误：未提供搜索目录路径"
    def _search_files(path, pattern, max_results):
        try:
            result = []
            count = 0
            for root, dirs, files in os.walk(path):
                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        file_path = os.path.join(root, filename)
                        result.append(file_path)
                        count += 1
                        if count >= max_results:
                            break
                if count >= max_results:
                    break
            
            if not result:
                return f"未找到匹配模式 '{pattern}' 的文件"
            
            return f"找到 {len(result)} 个匹配的文件:\n" + "\n".join(result)
        except FileNotFoundError:
            return f"错误：目录 '{path}' 不存在"
        except NotADirectoryError:
            return f"错误：'{path}' 不是目录"
        except Exception as e:
            return f"错误：搜索文件时发生异常 - {str(e)}"
    return _handle_permission_file(path, _search_files, pattern, max_results)

def _run_command_handler(params: Dict[str, str]):
    if _check_permission:
        result = _permission_manager.check_permission_for_cmd(params['command'])
        if not result.allowed:
            return f'命令执行失败：{result.reason}'
    command = params['command'].split(' ')
    return str(
        subprocess.run(
            command, 
            cwd=PATH_CONFIG.WORKSPACE_PATH,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
    )

# 定义 StrReplace 工具
StrReplace = Tool(
    name="StrReplace",
    description="替换指定文件中的字符串。在文件中查找指定的旧字符串，并将其替换为新字符串内容。只会替换第一个匹配项。",
    handler=_str_replace_handler,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要进行替换操作的文件路径"
            },
            "old_str": {
                "type": "string",
                "description": "要被替换的旧字符串内容"
            },
            "new_str": {
                "type": "string",
                "description": "替换后的新字符串内容"
            }
        },
        "required": ["path", "old_str"]
    }
)


# 定义 WriteFile 工具
WriteFile = Tool(
    name="WriteFile",
    description="写入新文件或覆盖现有文件。将指定的内容写入到指定路径的文件中。如果文件不存在会自动创建，如果存在则会覆盖原有内容。",
    handler=_write_file_handler,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要写入的文件路径"
            },
            "content": {
                "type": "string",
                "description": "要写入文件的全部内容"
            }
        },
        "required": ["path", "content"]
    }
)


# 定义 ReadFile 工具
ReadFile = Tool(
    name="ReadFile",
    description="读取指定文件的内容并返回。可以用于查看文件的完整内容。",
    handler=_read_file_handler,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要读取的文件路径"
            }
        },
        "required": ["path"]
    }
)


# 定义 ListFiles 工具
ListFiles = Tool(
    name="ListFiles",
    description="列出指定目录下的所有文件和子目录。可以用于查看目录结构。",
    handler=_list_files_handler,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要列出的目录路径"
            }
        },
        "required": ["path"]
    }
)


# 定义 SearchFiles 工具
SearchFiles = Tool(
    name="SearchFiles",
    description="在指定目录中搜索匹配文件名模式的文件。支持通配符模式，如 '*.py' 搜索所有 Python 文件。",
    handler=_search_files_handler,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要搜索的根目录路径"
            },
            "pattern": {
                "type": "string",
                "description": "文件名匹配模式（支持通配符），例如 '*.py'"
            },
            "max_results": {
                "type": "integer",
                "description": "最大结果数量",
                "default": 100
            }
        },
        "required": ["path"]
    }
)

RunCommand = Tool(
    name="RunCommand",
<<<<<<< HEAD
    description="根据命令使用subprocess进行运行",
=======
    description="根据命令使用subprocess进行运行，有概率出现编码问题。如果出现，请优先检查是否输出结果，否则忽略。",
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
    handler=_run_command_handler,
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "需要运行的整个命令，例如'python -c \"print('hello, world')\"'"
            }
        },
        "required": ["command"]
    }
)