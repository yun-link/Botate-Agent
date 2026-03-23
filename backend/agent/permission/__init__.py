"""
权限管理模块

提供文件访问权限管理功能，包括权限配置加载和路径权限检查。
"""

from .permission_manager import PermissionManager, PermissionCheckResult

__all__ = [
    "PermissionManager",
    "PermissionCheckResult",
]
