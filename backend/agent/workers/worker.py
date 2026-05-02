"""
Worker Agent 模块

继承 BaseAgent 的 Worker 实现，支持 Skill 管理和调用。
"""

import asyncio
from datetime import datetime, timedelta
import json
import uuid
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import platform

from model.message_schemas import Text, Content
from model.tool import register_tool
from agent.base_agent import BaseAgent
from agent.tools import load_public_tools
from agent.skill_manager import SkillManager, SkillResult
from agent.permission import PermissionManager, PermissionCheckResult
from agent.events import PermissionDeniedEvent
from model import (
    FunctionCallContent,
    Message,
    ModelConfig,
    ModelRouterConfig,
    ResponseContent,
    Tool,
)
from prompt_utils.prompt_utils import Prompt
from config import PATH_CONFIG, load_agent_config


class Worker(BaseAgent):
    """
    Worker Agent 类
    """
    system_prompt_path = PATH_CONFIG.PROMPTS_PATH / 'worker_prompts' / 'worker_system_prompt.md'
    user_prompt_path = PATH_CONFIG.PROMPTS_PATH / 'worker_prompts' / 'worker_user_prompt.md'
    prompt = Prompt.load_prompt_from_file(
        system_prompt_file_path=system_prompt_path, 
        user_prompt_file_path=user_prompt_path
    )

    def __init__(
        self,
        config: Union[ModelConfig, ModelRouterConfig],
        end_marker: str = "[任务结束]"
    ):
        """
        初始化 Worker Agent

        Args:
            config: 模型配置
            system_prompt: 系统提示词
            end_marker: 结束标记
        """
        # 初始化 SkillManager
        self.skill_manager = SkillManager()

        # 加载全局工具
        self.global_tools = load_public_tools()

        # 创建 skill 工具
        self.skill_tools = self._create_skill_tool()
        [register_tool(skill_tool) for skill_tool in self.skill_tools]
        

        # 合并所有工具
        self.all_tools = self.global_tools + self.skill_tools

        # 调用父类初始化
        super().__init__(
            config=config,
            tools=self.all_tools,
            end_marker=end_marker
        )

        # 存储当前激活的技能信息
        self.active_skill: Optional[str] = None
        self.active_skill_allowed_tools: List[str] = []

        # 初始化权限管理器
        self.permission_manager = PermissionManager()

        self._special_tools_and_handlers = {
            'skill': self.load_skill
        }

        # 添加系统提示消息
        self.add_message(self.prompt.system_prompt.to_message(), isimportant=True)

        # 定时保存记忆相关
        agent_config = load_agent_config()
        self._memory_save_interval = agent_config.MEMORY_SAVE_INTERVAL_HOURS * 3600  # 转换为秒
        self._last_memory_save_time = time.time()
        self._memory_save_task: Optional[asyncio.Task] = None
        
    def _create_skill_tool(self) -> Tool:
        """
        创建 skill 工具

        Returns:
            Tool 对象
        """
        async def skill_handler(params: dict) -> str:
            """
            处理 skill 工具调用（异步）

            Args:
                params: 包含 skill_name 的字典

            Returns:
                操作结果信息
            """
            return "正在加载Skill"

        return [
            Tool(
                name="skill",
                description=(f"加载并激活指定的技能。"
                            "调用后会将该技能的提示词添加到系统消息中，"
                            "并限制只能使用该技能允许的工具。"),
                handler=skill_handler,
                parameters={
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "要加载的技能名称"
                        }
                    },
                    "required": ["skill_name"]
                }
            )
        ]

    async def load_skill(self, params: Dict[str, Any]) -> SkillResult:
        """
        加载指定技能

        Args:
            skill_name: 技能名称

        Returns:
            SkillResult 对象
        """
        # 获取技能
        
        skill_name = params['skill_name']
        self.logger.info(f'加载Skill：{skill_name}')
        result = self.skill_manager.get_skill(skill_name)
        self.logger.info(f'技能结果：{result}')
        if result.success:
            # 将技能消息添加到消息列表
            for msg in result.messages:
                self.add_message(msg)

            # 更新当前激活的技能信息
            self.active_skill = skill_name

            self.active_skill_allowed_tools = result.allowed_tools

            # 如果有允许的工具列表，更新模型工具
            if result.allowed_tools:
                self._update_tools_by_skill(result.allowed_tools)

        return result

    def _update_tools_by_skill(self, allowed_tools: List[str]):
        """
        根据技能允许的工具列表更新模型工具

        Args:
            allowed_tools: 允许使用的工具名称列表
        """
        # 始终保留 skill 工具
        new_tools = [self.skill_tools]

        # 添加全局工具中允许的工具
        if allowed_tools:
            for tool in self.global_tools:
                if tool.name in allowed_tools:
                    new_tools.append(tool)

        # 更新模型工具
        self.model_tools.clear()
        self.model_tools.extend(
            [tool.schema.to_openai_format() for tool in new_tools]
        )

    def get_available_skills_info(self) -> dict:
        """
        获取所有可用技能的信息

        Returns:
            技能信息字典
        """
        skills_metadata = self.skill_manager.get_all_skills_metadata()
        return {
            skill_metadata.name:
            skill_metadata.description
            for skill_metadata in skills_metadata
        }

    async def _inner_loop(self) -> AsyncGenerator[ResponseContent, None]:
        """
        内部循环实现（异步）

        Returns:
            ResponseContent 异步生成器
        """
        async for chunk in self.call_model():
            yield chunk
    
    async def _run_tool(self, tool_call: FunctionCallContent) -> Any:
        """
        运行工具

        Args:
            tool_call: 工具调用对象

        Returns:
            工具执行结果，如果权限不足返回 PermissionDeniedEvent
        """
        tool_name = tool_call.name

        # 查找工具
        tool = None

        for t in self.all_tools:
            if t.name == tool_name:
                tool = t
                break

        if tool is None:
            return f"错误：未找到工具 '{tool_name}'"
            
        try:

            result = tool.execute(tool_call.params)
            if asyncio.iscoroutine(result):
                result = await result
            if isinstance(result, PermissionCheckResult):
                return PermissionDeniedEvent(
                    tool_name=tool_name,
                    reason=result.reason
                )
            return result
        except Exception as e:
            self.logger.error(e)
            return f"工具执行错误：{str(e)}"
    def _get_workspace_files(self):
        path = PATH_CONFIG.WORKSPACE_PATH
        items = os.listdir(path)
        result = []
        for item in items:
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                result.append(f"[DIR] {item}")
            else:
                result.append(f"[FILE] {item}")
        return "目录内容:\n" + "\n".join(result)
    async def run(
        self, task: List[Content]
    ) -> AsyncGenerator[Union[ResponseContent, str], None]:
        """
        运行 Worker 处理任务

        Args:
            task: 用户任务内容列表

        Yields:
            ResponseContent 或轮次结束标记
        """

        # 从 task 中提取文本用于格式化 prompt
        self.logger.info(f'Agent 开始运行-task：{str(task)[:100]}')
        task_text = ""
        for content in task:
            if isinstance(content, Text):
                task_text += content.content
        
        # 添加用户消息
        self.prompt.user_prompt.format(
            task=task_text,
            skills_list=str(self.get_available_skills_info()),
            workspace_path=str(PATH_CONFIG.WORKSPACE_PATH),
            workspace_files=self._get_workspace_files(),
            time=datetime.now(),
            os=platform.platform()
        )
        user_message = self.prompt.user_prompt.to_message()
        self.add_message(user_message, isimportant=True)

        # 运行主循环
        try:
            async for result in self._main_loop():
                yield result
        finally:
            # 任务结束时取消后台任务
            if self._memory_save_task is not None:
                self._memory_save_task.cancel()
                try:
                    await self._memory_save_task
                except asyncio.CancelledError:
                    pass