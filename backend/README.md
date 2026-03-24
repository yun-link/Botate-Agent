# Botate-Agent Backend

基于大语言模型的 Agent 框架后端，提供流式响应、工具调用、技能管理和长期记忆功能。

## 功能特性

- **流式响应**: 使用 Server-Sent Events (SSE) 实现实时流式输出
- **多模型支持**: 支持多种 LLM 提供商 (OpenAI 兼容接口)
- **工具系统**: 内置文件操作工具，支持动态工具扩展
- **技能管理**: 动态加载和管理 AI 技能 (Skills)
- **长期记忆**: 基于向量检索的记忆库系统
- **函数调用**: 支持模型 function calling 能力

## 项目结构

```
backend/
├── agent/                      # Agent 核心实现
│   ├── base_agent.py          # Agent 基类，包含主循环逻辑
│   ├── context.py             # 消息上下文管理
│   ├── events.py              # 事件定义
│   ├── workers/               # Worker Agent 实现
│   │   └── worker.py          # 技能支持的 Worker
│   ├── tools/                 # 工具实现
│   │   ├── basic_tools.py     # 基础工具 (StrReplace, WriteFile)
│   │   ├── memory_bank.py     # 记忆库工具
│   │   └── search.py          # 搜索工具
│   ├── skill_manager/         # 技能管理器
│   │   ├── skill_manager.py   # 技能加载和管理
│   │   └── skill_schema.py    # 技能定义
│   └── memory_bank/           # 记忆库实现
│       ├── memory_bank.py     # 记忆库核心
│       ├── memory.py          # 记忆条目
│       └── models.py          # 数据模型
├── api/                       # FastAPI 接口
│   ├── agent_api.py           # Agent API 端点
│   └── models.py              # 请求/响应模型
├── model/                     # 模型层
│   ├── model.py               # Model 类，统一入口
│   ├── providers/             # 提供商实现
│   │   ├── base_provider.py   # 基类
│   │   └── openai_compatible.py  # OpenAI 兼容接口
│   ├── model_router/          # 模型路由器
│   ├── message_schemas/       # 消息结构定义
│   └── tool/                  # 工具 schema
│       └── mcp/               # MCP 协议支持
├── config/                    # 配置
│   ├── config_model.py        # 配置数据类
│   ├── mcp_servers.json       # MCP 服务器配置
│   └── provider_infos/        # 提供商配置
│       ├── siliconflow.json
│       ├── deepseek.json
│       ├── kimi.json
│       └── volcengine.json
├── assets/                    # 资源文件
│   ├── skills/                # 技能定义 (SKILL.md)
│   ├── prompts/               # 提示词模板
│   └── memory_bank/           # 记忆库存储 (SQLite)
├── prompt_utils/              # 提示词工具
├── logs/                      # 日志输出
└── run.sh                     # 启动脚本
```

## 快速开始

### 环境要求

- Python 3.10+
- 相关依赖 (见下方)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Key

通过环境变量配置各提供商的 API Key:

```bash
# SiliconFlow
export SF_API_KEY="your-api-key"

# DeepSeek
export DEEPSEEK_API_KEY="your-api-key"

# Kimi (Moonshot)
export KIMI_API_KEY="your-api-key"

# Volcengine
export VOLCENGINE_API_KEY="your-api-key"
```

### 启动服务

```bash
# 方式 1: 使用脚本
bash backend/run.sh

# 方式 2: 直接运行
python -m backend.api.agent_api
```

服务默认运行在 `http://localhost:8000`

## API 接口

### 调用 Agent

**端点**: `POST /api/agent/call`

使用 SSE 流式返回结果:

```bash
curl -X POST http://localhost:8000/api/agent/call \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"type": "text", "text": "你好，请介绍一下自己"}]
  }'
```

**请求体**:

```python
{
    "task_id": "optional-task-id",  # 可选，默认自动生成
    "contents": [
        {"type": "text", "text": "用户输入内容"}
    ]
}
```

**响应事件类型**:

- `answer`: 回答内容
- `reasoning`: 推理过程
- `function_call`: 函数调用
- `task_started`: 任务开始
- `task_completed`: 任务完成

### 查询任务进度

**端点**: `POST /api/agent/progress`

```bash
curl -X POST http://localhost:8000/api/agent/progress \
  -H "Content-Type: application/json" \
  -d '{"task_id": "your-task-id"}'
```

### 获取对话消息

**端点**: `POST /api/agent/messages`

```bash
curl -X POST http://localhost:8000/api/agent/messages \
  -H "Content-Type: application/json" \
  -d '{"task_id": "your-task-id"}'
```

## 工具系统

### 内置工具

| 工具名称 | 功能 |
|---------|------|
| StrReplace | 替换文件中的字符串 |
| WriteFile | 写入或创建文件 |
| memory_bank | 记忆库操作 |
| skill | 技能加载 |

### 扩展工具

可以通过实现 `Tool` 类来扩展工具:

```python
from model.tool import Tool

def my_handler(params: dict) -> str:
    # 处理逻辑
    return "结果"

my_tool = Tool(
    name="my_tool",
    description="工具描述",
    handler=my_handler,
    parameters={...}  # JSON Schema
)
```

## 技能系统

技能存放在 `backend/assets/skills/` 目录下，每个技能是一个文件夹，包含 `SKILL.md` 文件。

### SKILL.md 格式

```yaml
---
name: skill_name
description: 技能描述
version: 1.0.0
license: MIT
allowed-tools:
  - tool1
  - tool2
---

# 技能提示词内容

这里定义技能的系统提示词...
```

### 使用技能

Agent 可以通过 `skill` 工具动态加载技能:

```
请加载 search 技能，然后搜索关于 Python 异步编程的资料
```

## 记忆库系统

基于向量检索的长期记忆系统，支持:

- **语义搜索**: 通过向量相似度检索相关记忆
- **重排序**: 使用 reranker 模型优化排序结果
- **自动摘要**: 使用 LLM 生成记忆摘要

### 配置

在 `config/config_model.py` 中配置:

```python
@dataclass
class MemoryBankConfig:
    EMBEDDING_MODEL: str = "qwen3-embedding-8b"
    RERANKER_MODEL: str = "qwen3-reranker-8b"
    SUMMARY_MODEL: str = "doubao-seed-1.6-lite"
```

## 模型配置

### 默认配置

- **Worker Agent 模型**: `doubao-seed-1.8`
- **记忆摘要模型**: `doubao-seed-1.6-lite`
- **嵌入向量模型**: `qwen3-embedding-8b`
- **重排序模型**: `qwen3-reranker-8b`

### 添加新模型

在 `config/provider_infos/` 目录下添加新的提供商配置 JSON 文件:

```json
{
    "provider_type": "openai_compatible",
    "provider_name": "provider_name",
    "base_url": "https://api.provider.com/v1/",
    "models": {
        "model-name": {
            "model_id": "provider/model-id",
            "thinking": {
                "support_thinking": true
            }
        }
    }
}
```

## 日志

日志文件保存在 `backend/logs/agent_api.log`

可以通过 `config/config_model.py` 修改日志配置。

## 技术栈

- **FastAPI**: Web 框架
- **Pydantic**: 数据验证
- **numpy**: 向量计算
- **SQLite**: 记忆库存储
- **OpenAI SDK**: API 调用 (兼容格式)

## 许可证

MIT License
