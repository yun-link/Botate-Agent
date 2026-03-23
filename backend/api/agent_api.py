"""
Agent API 模块

提供 Agent 相关的 FastAPI 路由，使用 SSE 实现流式响应
"""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any, List
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from model.message_schemas import Message, AnswerContent, ReasoningContent, FunctionCallContent
from agent.workers import Worker
from agent.events import (
    AnswerBeginEvent, 
    ReasoningBeginEvent, 
    FunctionCallInfoEvent, 
    RoundEndEvent,
    PermissionDeniedEvent
)
from config.config import load_agent_config, load_path_config
from api.models import AgentCallRequest, PermissionConfirmRequest
from loggers import get_logger

path_config = load_path_config()

api_logger = get_logger('api')

os.chdir(path_config.WORKSPACE_PATH)


class GlobalState:
    """
    全局状态管理类
    """
    def __init__(self):
        self.worker: Optional[Worker] = None
        self.config = None
        self.chunks: List[Dict[str, Any]] = []
        self.is_running: bool = False
        self.messages: List[Message] = []
    
    def reset(self):
        """重置状态"""
        self.chunks = []
        self.is_running = False
        self.messages = []
    
    def get_or_create_worker(self) -> Worker:
        """获取或创建 Worker 实例"""
        if self.worker is None or self.config is None:
            self.config = load_agent_config()
            self.worker = Worker(config=self.config.WOKRER_AGENT_MODEL)
        return self.worker


# 全局状态实例
state = GlobalState()


async def run_agent_async(user_contents: list):
    """
    运行 Agent 任务
    """
    try:
        worker = state.get_or_create_worker()
        state.is_running = True
        state.chunks = []
        
        # 添加用户消息
        user_message = Message(role='user', content=user_contents)
        state.messages.append(user_message)
        
        # 发送任务开始事件
        state.chunks.append({
            "type": "event",
            "event": "task_started",
            "timestamp": str(datetime.now())
        })
        
        full_answer = ""
        full_reasoning = ""
        tool_calls_in_round = []
        
        async for result in worker.run(user_contents):
            chunk_data = None
            
            if isinstance(result, AnswerContent):
                content = result.content
                content_text = content.to_text() if hasattr(content, 'to_text') else str(content)
                chunk_data = {"type": "answer", "content": content_text}
                full_answer += content_text
                
            elif isinstance(result, ReasoningContent):
                content = result.content
                content_text = content.to_text() if hasattr(content, 'to_text') else str(content)
                chunk_data = {"type": "reasoning", "content": content_text}
                full_reasoning += content_text
                
            elif isinstance(result, FunctionCallContent):
                chunk_data = result.model_dump()
                # 收集工具调用（带结果的）
                if result.result is not None:
                    tool_calls_in_round.append(result)
                
            elif isinstance(result, PermissionDeniedEvent):
                chunk_data = {
                    "type": "event",
                    "event": "permission_denied",
                    "tool_name": result.tool_name,
                    "reason": result.reason
                }
                
            elif isinstance(result, RoundEndEvent):
                # 轮次结束，添加助手消息和工具消息
                if full_answer or tool_calls_in_round or full_reasoning:
                    assistant_message = Message(role='assistant', content=full_answer)
                    assistant_message.reasoning_content = full_reasoning if full_reasoning else None
                    assistant_message.tool_calls = tool_calls_in_round
                    state.messages.append(assistant_message)
                    
                    # 添加工具消息
                    for tool_call in tool_calls_in_round:
                        tool_message = Message(role='tool', content=tool_call)
                        state.messages.append(tool_message)
                    
                    tool_calls_in_round = []
                    full_answer = ""
                    full_reasoning = ""
                
                chunk_data = result.model_dump()
            
            elif isinstance(result, (AnswerBeginEvent, ReasoningBeginEvent, FunctionCallInfoEvent)):
                chunk_data = result.model_dump()
            
            if chunk_data:
                state.chunks.append(chunk_data)
        
        # 添加最后的助手消息（如果有内容且未通过 RoundEndEvent 添加）
        if full_answer or tool_calls_in_round:
            assistant_message = Message(role='assistant', content=full_answer)
            assistant_message.tool_calls = tool_calls_in_round
            state.messages.append(assistant_message)
            
            for tool_call in tool_calls_in_round:
                tool_message = Message(role='tool', content=tool_call)
                state.messages.append(tool_message)
        
        # 任务完成
        state.chunks.append({
            "type": "event",
            "event": "task_completed",
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        api_logger.error(e)
        state.chunks.append({
            "type": "error",
            "message": str(e),
            "timestamp": str(datetime.now())
        })
    finally:
        state.is_running = False


# 创建 FastAPI 应用
app = FastAPI(title="Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/agent/call")
async def call_agent(request: AgentCallRequest):
    """
    调用 Agent 开始新任务
    
    如果已有运行中的任务，返回错误
    """
    if state.is_running:
        raise HTTPException(status_code=400, detail="已有任务正在运行")
    
    # 启动任务
    asyncio.create_task(run_agent_async(request.contents))
    api_logger.info('调用Agent')
    
    async def event_generator() -> AsyncGenerator[str, None]:
        last_chunk_index = 0
        
        try:
            while True:
                while last_chunk_index < len(state.chunks):
                    chunk = state.chunks[last_chunk_index]
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    last_chunk_index += 1
                    
                    if chunk.get("type") == "event" and chunk.get("event") == "task_completed":
                        return
                    if chunk.get("type") == "error":
                        return
                
                if not state.is_running and last_chunk_index >= len(state.chunks):
                    yield f"data: {json.dumps({'type': 'event', 'event': 'stream_end'}, ensure_ascii=False)}\n\n"
                    return
                
                await asyncio.sleep(0.1)
                    
        except Exception as e:
            api_logger.error(e)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/agent/progress")
async def get_progress():
    """
    获取当前任务进度
    
    如果有 chunks 返回 SSE 流续接，没有则返回结束标记
    """
    api_logger.info('查询进度')
    async def progress_generator() -> AsyncGenerator[str, None]:
        if not state.chunks:
            yield f"data: {json.dumps({'type': 'event', 'event': 'stream_end'}, ensure_ascii=False)}\n\n"
            return
        
        last_chunk_index = 0
        
        try:
            while True:
                while last_chunk_index < len(state.chunks):
                    chunk = state.chunks[last_chunk_index]
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    last_chunk_index += 1
                    
                    if chunk.get("type") == "event" and chunk.get("event") == "task_completed":
                        return
                    if chunk.get("type") == "error":
                        return
                
                if not state.is_running and last_chunk_index >= len(state.chunks):
                    yield f"data: {json.dumps({'type': 'event', 'event': 'stream_end'}, ensure_ascii=False)}\n\n"
                    return
                
                await asyncio.sleep(0.1)
                    
        except Exception as e:
            api_logger.error(e)
    
    return StreamingResponse(
        progress_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/agent/messages")
async def get_display_messages():
    """
    获取显示消息列表
    """
    api_logger.info('获取消息列表')
    return {
        "messages": [msg.model_dump() for msg in state.messages],
        "is_running": state.is_running
    }


@app.post("/api/agent/permission/confirm")
async def confirm_permission(request: PermissionConfirmRequest):
    """
    确认权限请求
    """
    api_logger.info('确认权限请求')
    worker = state.get_or_create_worker()
    
    if worker.permission_event is None:
        return {
            "success": False,
            "message": "当前没有待确认的权限请求"
        }
    
    # 设置确认结果并触发事件
    worker.permission_allowed = request.allowed
    worker.permission_event.set()
    
    return {
        "success": True,
        "message": "权限已确认" if request.allowed else "权限已拒绝"
    }


@app.post("/api/agent/reset")
async def reset_agent():
    """重置 Agent 状态"""
    api_logger.info('重置状态')
    state.reset()
    if state.worker:
        state.worker = Worker(state.config.WOKRER_AGENT_MODEL)
    return {"success": True, "message": "状态已重置"}


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
