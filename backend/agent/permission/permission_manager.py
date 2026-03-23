"""
权限管理器模块

提供文件访问权限检查和管理功能。
"""

import json
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

from pydantic import BaseModel

from config.config import PermissionConfig, FolderPermission, load_permission_config
from loggers import get_logger

class PermissionCheckResult(BaseModel):
    """
    权限检查结果
    
    Attributes:
        allowed: 是否允许访问
        reason: 拒绝原因（如果不允许）
    """
    allowed: bool
    reason: Optional[str] = None


class PermissionManager:
    """
    权限管理器
    
    负责加载权限配置并检查文件路径的访问权限。
    """

    def __init__(self, config: Optional[PermissionConfig] = None):
        """
        初始化权限管理器
        
        Args:
            config: 权限配置，如果为 None 则加载默认配置
        """
        self.config = config or load_permission_config()
        self._pending_confirmations: dict[str, dict] = {}  # 存储待确认的操作
        self.logger = get_logger('permission')
    
    def check_permission_for_file(
        self, 
        file_path: str, 
        operation: Literal["read", "write", "any"] = "any"
    ) -> PermissionCheckResult:
        """
        检查文件路径是否符合权限设置
        
        Args:
            file_path: 要检查的文件路径
            operation: 操作类型，"read"、"write" 或 "any"
            tool_name: 工具名称，用于确定操作类型
            
        Returns:
            PermissionCheckResult: 权限检查结果
        """
        
        # 检查是否在配置的文件夹列表中
        matched_folder = None
        file_path = Path(file_path)
        for folder_perm in self.config.folders:
            folder_path = Path(folder_perm.path)
            try:
                # 检查路径是否在文件夹内或是文件夹本身
                if file_path == folder_path or folder_path in file_path.parents or file_path.is_relative_to(folder_path):
                    matched_folder = folder_perm
                    break
            except Exception:
                continue
        self.logger.info(f'目标访问文件：{file_path} 校验后文件：{matched_folder}')
        if self.config.mode == "blacklist":
            # 黑名单模式：默认允许，匹配的文件夹根据配置决定
            if matched_folder is None:
                # 不在黑名单中，允许访问
                return PermissionCheckResult(
                    allowed=True,
                )
            
            # 在黑名单中，根据 access_mode 决定
            if matched_folder.access_mode == "denied":
                return PermissionCheckResult(
                    allowed=False,
                    reason=f"路径 '{file_path}' 在禁止访问列表中",
                )
            elif matched_folder.access_mode == "read_only":
                if operation == "write":
                    return PermissionCheckResult(
                        allowed=False,
                        reason=f"路径 '{file_path}' 为只读访问，不允许写入操作",
                    )
                return PermissionCheckResult(
                    allowed=True,
                )
            else:  # read_write
                return PermissionCheckResult(
                    allowed=True,
                )
        
        else:  # whitelist mode
            # 白名单模式：默认禁止，只有匹配的文件夹允许访问
            if matched_folder is None:
                return PermissionCheckResult(
                    allowed=False,
                    reason=f"路径 '{file_path}' 不在允许访问的文件夹列表中",
                )
            
            # 在白名单中，根据 access_mode 决定
            if matched_folder.access_mode == "denied":
                return PermissionCheckResult(
                    allowed=False,
                    reason=f"路径 '{file_path}' 被禁止访问",
                )
            elif matched_folder.access_mode == "read_only":
                if operation == "write":
                    return PermissionCheckResult(
                        allowed=False,
                        reason=f"路径 '{file_path}' 为只读访问，不允许写入操作",
                    )
                return PermissionCheckResult(
                    allowed=True
                )
            else:  # read_write
                return PermissionCheckResult(
                    allowed=True,
                )
    def check_permission_for_cmd(
        self,
        command: str
    ):
        command = command.split(' ')
        if command[0] in self.config.not_allowed_commands:
            return PermissionCheckResult(
                    allowed=False,
                    reason='该命令不被允许'
                )
        for arg in command:
            try:
                result = self.check_permission_for_file(arg)
                if not result.allowed:
                    return result
            except ValueError:
                pass
        return PermissionCheckResult(
                    allowed=True
                )
