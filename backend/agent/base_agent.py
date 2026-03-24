from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable, Dict, List, Optional, Union, Any
import asyncio
import json

from model import (
    Model,
    ModelConfig,
    ModelRouter,
    ModelRouterConfig,
    load_model_from_config,
    Message,
    ResponseContent,
    FunctionCallContent,
    AnswerContent,
    ReasoningContent,
    Tool,
)

from agent.events import (
    AnswerBeginEvent,
    ReasoningBeginEvent,
    FunctionCallInfoEvent,
    RoundEndEvent,
    PermissionDeniedEvent
)
from agent.context import MessageContext
from agent.memory_bank import MemoryBank, load_memory_bank
from agent.tools.basic_tools import set_check_permission
from loggers import get_logger


class BaseAgent(ABC):
    """
    Agent 基类
    
    提供模型加载、消息管理、工具调用处理等核心功能。
    子类需要实现 _inner_loop 和 _run_tool 方法。
    """
    
    def __init__(
        self,
        config: Union[ModelConfig, ModelRouterConfig],
        tools: Optional[List[Union[Tool, dict]]] = None,
        end_marker: str = "[任务结束]",
        memory_bank: Optional[MemoryBank] = None,
        sliding_window_size: int = 0
    ):
        """
        初始化 Agent
        
        Args:
            config: 模型配置，可以是 ModelConfig 或 ModelRouterConfig
            tools: 工具列表，可以是 Tool 对象或字典
            end_marker: 结束标记，用于检测任务完成
            memory_bank: 记忆库实例，如果为 None 则使用全局记忆库
            sliding_window_size: 滑动窗口大小，用于限制消息历史长度
        """
        self.config = config
        self.tools = tools or []
        self.end_marker = end_marker
        
        # 加载模型
        self.model = load_model_from_config(
            config,
            tools=self.tools
        )

        self.model_tools = self.model.tools
        
        # 初始化消息上下文
        if memory_bank is None:
            memory_bank = load_memory_bank()
        self.message_context = MessageContext(
            messages=self.model.messages,
            memory_bank=memory_bank,
            sliding_window_size=sliding_window_size
        )
        
        # 权限确认相关状态
        self.permission_event: Optional[asyncio.Event] = None
        self.permission_allowed: Optional[bool] = None

        self._special_tools_and_handlers: Dict[str, Callable] = {}

        self.logger = get_logger('main')
    
    def _check_end(self, text: str) -> bool:
        """
        检查文本中是否包含结束标记
        
        Args:
            text: 要检查的文本
            
        Returns:
            如果包含结束标记返回 True，否则返回 False
        """
        return self.end_marker in text
    
    @abstractmethod
    def _inner_loop(self) -> AsyncGenerator[ResponseContent, None]:
        """
        内部循环，由子类实现
        
        该函数应该返回一个基类为 ResponseContent 的异步生成器。
        
        Returns:
            AsyncGenerator[ResponseContent, None]: 响应内容的异步生成器
        """
        pass
    
    @abstractmethod
    async def _run_tool(self, tool_call: FunctionCallContent) -> Any:
        """
        运行工具，由子类实现
        
        Args:
            tool_call: 工具调用对象，包含工具名称、参数等信息
            
        Returns:
            工具执行结果
        """
        pass
    
    async def _process_chunks(
        self,
        result_generator: AsyncGenerator[ResponseContent, None]
    ) -> AsyncGenerator[Union[ResponseContent, tuple], None]:
        """
        处理异步生成器中的每个 chunk，收集内容并返回汇总信息
        
        Args:
            result_generator: _inner_loop 返回的异步生成器
            
        Yields:
            ResponseContent: 响应内容（AnswerContent 或 ReasoningContent）
            Event: 事件（AnswerBeginEvent, ReasoningBeginEvent, FunctionCallInfoEvent）
            最后 yield 一个 tuple: (full_answer, full_reason, tool_calls)
        """
        # 用于收集各类内容
        answer_parts = []
        reason_parts = []
        tool_calls = []
        
        # 当前处理的工具
        cur_tool = None
        cur_params = []
        
        # 标记是否已经发送了开始事件
        answer_begin_sent = False
        reason_begin_sent = False
        
        # 遍历异步生成器的每个 chunk
        async for chunk in result_generator:
            if isinstance(chunk, FunctionCallContent):
                if cur_tool is not None and chunk.index != cur_tool.index:
                    # index 变化，保存之前的工具
                    cur_tool.params = "".join(cur_params)
                    tool_calls.append(cur_tool)
                    # 发送工具调用事件
                    yield FunctionCallInfoEvent(tool_name=cur_tool.name)
                    cur_params = []
                yield chunk
                cur_tool = chunk
                cur_params.append(chunk.params)
                
            elif isinstance(chunk, AnswerContent):
                # 处理回答内容
                # 首次遇到 AnswerContent 时发送 AnswerBeginEvent
                if not answer_begin_sent:
                    yield AnswerBeginEvent()
                    answer_begin_sent = True
                
                # 提取文本内容用于检查结束标记
                if hasattr(chunk, 'content'):
                    if isinstance(chunk.content, str):
                        answer_parts.append(chunk.content)
                    elif hasattr(chunk.content, 'content'):
                        answer_parts.append(chunk.content.content)
                yield chunk
                        
            elif isinstance(chunk, ReasoningContent):
                # 处理推理内容
                # 首次遇到 ReasoningContent 时发送 ReasoningBeginEvent
                if not reason_begin_sent:
                    yield ReasoningBeginEvent()
                    reason_begin_sent = True
                
                # 提取文本内容
                if hasattr(chunk, 'content'):
                    if isinstance(chunk.content, str):
                        reason_parts.append(chunk.content)
                    elif hasattr(chunk.content, 'content'):
                        reason_parts.append(chunk.content.content)
                yield chunk
        
        # 处理最后一个工具
        if cur_tool is not None:
            cur_tool.params = "".join(cur_params)
            tool_calls.append(cur_tool)
            # 发送工具调用事件
            yield FunctionCallInfoEvent(tool_name=cur_tool.name)
        
        # 拼接完整的回答和推理内容
        full_answer = "".join(answer_parts)
        full_reason = "".join(reason_parts)
        
        # 最后返回汇总信息
        yield (full_answer, full_reason, tool_calls)
    
    async def _main_loop(self) -> AsyncGenerator[Union[ResponseContent, AnswerBeginEvent, ReasoningBeginEvent, FunctionCallInfoEvent, RoundEndEvent], None]:
        """
        主循环，包含核心逻辑
        
        无限循环调用 _inner_loop，处理响应内容、工具调用，
        直到检测到结束标记为止。
        
        Yields:
            ResponseContent: 响应内容
            Event: 各类事件（AnswerBeginEvent, ReasoningBeginEvent, FunctionCallInfoEvent, RoundEndEvent）
        """
        while True:
            # 调用内部循环获取异步生成器
            result_generator = self._inner_loop()
            
            # 处理 chunks 并收集内容
            full_answer = ""
            full_reason = ""
            tool_calls = []
            
            async for result in self._process_chunks(result_generator):
                if isinstance(result, tuple):
                    # 这是最后的汇总信息
                    full_answer, full_reason, tool_calls = result
                else:
                    # 这是 ResponseContent
                    yield result
            
            # 检查是否包含结束标记
            if self._check_end(full_answer):
                break
            
            # 处理工具调用
            assistant_message = Message(role='assistant', content=full_answer)
            assistant_message.tool_calls = []
            tool_call_messages = []
            
            if full_reason:
                assistant_message.reasoning_content = full_reason
            
            for tool in tool_calls:
                # 解析工具参数 JSON
                try:
                    tool.params = json.loads(tool.params)
                except json.JSONDecodeError:
                    tool.result = "工具调用参数JSON格式解析错误，请尝试重新调用工具"
                
                if isinstance(tool.params, dict):
                    # 调用子类实现的 _run_tool 方法
                    try:
                        tool.result = await self._run_tool(tool)
                        
                        if isinstance(tool.result, PermissionDeniedEvent):
                            # 发送权限不足事件
                            yield tool.result
                            
                            # 等待用户确认
                            self.permission_event = asyncio.Event()
                            await self.permission_event.wait()
                            
                            if self.permission_allowed:
                                set_check_permission(False)
                                tool.result = await self._run_tool(tool)
                                set_check_permission(True)
                            else:
                                tool.result = '用户授权不通过'
                            
                            # 重置权限状态
                            self.permission_event = None
                            self.permission_allowed = None
                        if tool.name in self._special_tools_and_handlers:
                            await self._special_tools_and_handlers[tool.name](tool.params)
                        yield tool
                    except Exception as e:
                        tool.result = str(e)
                        self.logger.error(e)
                
                # 创建工具消息
                tool_call_messages.append(Message(role="tool", content=tool))
                assistant_message.tool_calls.append(tool)
            
            # 添加消息到模型
            self.add_message(assistant_message)
            for tool_message in tool_call_messages:
                self.add_message(tool_message)
            
            # 返回轮次结束事件
            yield RoundEndEvent()
    
    def add_message(self, message: Message, isimportant: bool = False):
        """
        添加消息到消息上下文
        
        Args:
            message: 要添加的消息
            isimportant: 是否为重要消息（不会被滑动窗口删除）
        """
        self.message_context.add_message(message, isimportant)
        self.logger.info(f'添加消息：{str(message)[:100]}')
    
    async def call_model(self, **kwargs) -> AsyncGenerator[ResponseContent, None]:
        """
        调用模型
        
        Args:
            **kwargs: 传递给模型 call_model_async 方法的参数
            
        Yields:
            ResponseContent: 模型响应内容
        """
        self.logger.info(f'调用模型')
        async for chunk in self.model.call_model_async(**kwargs):
            yield chunk
    
    def clear_messages(self):
        """清空消息历史"""
        self.message_context.messages.clear()
        self.model.clear_messages()
