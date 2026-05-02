<div align="center">

![logo](./.images/Logo.png)

</div>

<div align="center">

![visitors](https://visitor-badge.laobi.icu/badge?page_id=yunlink/Botate-Agent)
[![GitHub Repo stars](https://img.shields.io/github/stars/yunlink/Botate-Agent?style=social)](https://github.com/yunlink/Botate-Agent/stargazers)
[![GitHub Code License](https://img.shields.io/github/license/yunlink/Botate-Agent)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/yunlink/Botate-Agent)](https://github.com/yunlink/Botate-Agent/commits/master)
[![GitHub pull request](https://img.shields.io/badge/PRs-welcome-blue)](https://github.com/yunlink/Botate-Agent/pulls)

</div>

## 项目简介

Botate-Agent 是一个现代化的 AI Agent 系统，采用前后端分离架构：
- **后端**: 基于 FastAPI 构建的 Python 服务，提供 Agent 核心能力
- **前端**: 基于 React 的现代化聊天界面，提供流畅的用户体验

## 功能特性

### 核心能力
- 🤖 **智能 Agent**: 基于 LLM 的自主任务处理能力
- 📡 **流式响应**: 实时流式输出，支持 Server-Sent Events (SSE)
- 🔧 **工具系统**: 内置文件操作工具，支持动态工具扩展
- 🧠 **技能管理**: 动态加载和管理 AI 技能 (Skills)
- 💾 **长期记忆**: 基于向量检索的记忆库系统，支持语义搜索
- 📞 **函数调用**: 支持模型 function calling 能力

### 更新日志
<details> 
<summary> <b>[v2.1.0] - 2026-05-02</b></summary>
- 前端界面新增视窗详情
- 记忆库功能大规模简化
- 日志和记忆库在用户目录保存
- 模型信息更新：
    * 移除 DeepSeek-V3.2 系列模型，支持 DeepSeek-V4 系列模型
    * 移除 doubao-seed-1.6-lite 模型，支持 doubao-seed-2.0 模型
    * 移除 Kimi-K2 系列模型，支持 Kimi-K2.6 系列模型
    * 默认上下文模型更新为 doubao-seed-2.0-mini 模型
    * 默认 Worker 模型更新为 DeepSeek-V4-flash 模型
</details>

<details> 
<summary> <b>[v2.0.0] - 2026-03-24</b></summary>
- 2.0 版本发布，包含Agent核心功能
- 新增记忆库系统
- 新增技能系统
- 新增工具系统
- 新增权限系统
- 新增事件系统
- 新增日志系统
</details> 

### 前端特性
- 💬 实时聊天界面，支持流式响应
- 🧠 显示助手的推理过程
- 🔧 工具调用可视化与执行
- 📎 支持多模态输入（文本、图片、视频、音频、文件）
- 🔄 自动重连和进度流式传输
- 🎨 简洁现代的 UI 设计

## 技术栈

### 后端
- **FastAPI** - Web 框架
- **Pydantic** - 数据验证
- **OpenAI SDK** - API 调用 (兼容格式)

### 前端
- **React 19** - UI 框架
- **TypeScript** - 类型安全
- **Vite 8** - 构建工具和开发服务器
- **Axios** - HTTP 客户端
- **lucide-react** - 图标库

## 快速开始

### 环境要求

- **后端**: Python 3.10+
- **前端**: Node.js 20+
- **系统**: Windows / macOS / Linux

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd Botate-Agent
```

#### 2. 一键安装依赖（推荐）

```bash
# Linux/macOS
bash setup.sh

# Windows
setup.cmd
```

#### 或手动安装

##### 后端设置

```bash
cd backend

# 创建虚拟环境 (可选)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 或使用脚本
bash setup.sh        # Linux/macOS
setup.cmd            # Windows
```

##### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 或使用脚本
bash setup.sh        # Linux/macOS
setup.cmd            # Windows
```

#### 3. 配置 API Key

通过环境变量配置 LLM 提供商的 API Key:

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

#### 启动后端

```bash
# Linux/macOS
bash backend/run.sh

# Windows
backend\run.cmd

# 或直接运行
python -m backend.api.agent_api
```

后端服务默认运行在 `http://localhost:8000`

#### 启动前端

```bash
# Linux/macOS
bash frontend/run.sh

# Windows
frontend\run.cmd

# 或直接运行
cd frontend && npm run dev
```

前端服务默认运行在 `http://localhost:5173`

#### 一键启动全部服务

```bash
# Linux/macOS
bash run.sh

# Windows
run.cmd
```

现在可以在浏览器中打开 `http://localhost:5173` 开始使用。

## 项目结构

```
Botate-Agent/
├── backend/                      # 后端服务
│   ├── agent/                    # Agent 核心实现
│   │   ├── base_agent.py         # Agent 基类，包含主循环逻辑
│   │   ├── context.py            # 消息上下文管理
│   │   ├── events.py             # 事件定义
│   │   ├── workers/              # Worker Agent 实现
│   │   ├── tools/                # 工具实现
│   │   ├── skill_manager/        # 技能管理器
│   │   └── memory_bank/          # 记忆库实现
│   ├── api/                      # FastAPI 接口
│   │   ├── agent_api.py          # Agent API 端点
│   │   └── models.py             # 请求/响应模型
│   ├── model/                    # 模型层
│   │   ├── model.py              # Model 类，统一入口
│   │   ├── providers/            # 提供商实现
│   │   ├── model_router/         # 模型路由器
│   │   ├── message_schemas/      # 消息结构定义
│   │   └── tool/                 # 工具 schema
│   ├── config/                   # 配置
│   │   ├── config.py             # 配置数据类
│   │   ├── mcp_servers.json      # MCP 服务器配置
│   │   └── provider_infos/       # 提供商配置
│   ├── assets/                   # 资源文件
│   │   ├── skills/               # 技能定义 (SKILL.md)
│   │   ├── prompts/              # 提示词模板
│   │   └── memory_bank/          # 记忆库存储 (SQLite)
│   ├── prompt_utils/             # 提示词工具
│   ├── loggers/                  # 日志模块
│   ├── main.py                   # 入口文件
│   └── requirements.txt          # Python 依赖
│
├── frontend/                     # 前端应用
│   ├── src/
│   │   ├── components/           # React 组件
│   │   │   ├── AssistantMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── DetailPanel.tsx
│   │   │   ├── EventBar.tsx
│   │   │   ├── ReasoningBlock.tsx
│   │   │   ├── ToolCallBlock.tsx
│   │   │   ├── UserMessage.tsx
│   │   │   └── index.ts
│   │   ├── services/             # API 服务
│   │   │   └── api.ts            # 后端 API 集成
│   │   ├── types/                # TypeScript 类型定义
│   │   │   └── index.ts
│   │   ├── assets/               # 静态资源
│   │   ├── App.tsx               # 主应用组件
│   │   ├── App.css               # 应用样式
│   │   ├── main.tsx              # 入口文件
│   │   └── index.css             # 全局样式
│   ├── public/                   # 公共静态文件
│   ├── index.html                # HTML 模板
│   ├── vite.config.ts            # Vite 配置
│   ├── tsconfig.json             # TypeScript 配置
│   ├── package.json              # 依赖配置
│   └── README.md                 # 前端文档
│
└── README.md                     # 项目文档
```

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

```json
{
    "task_id": "optional-task-id",
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

### 其他接口

| 接口地址 | 方法 | 说明 |
|----------|------|------|
| `/api/agent/call` | POST | 发送消息到 Agent（SSE 流式） |
| `/api/agent/messages` | POST | 获取消息历史 |
| `/api/agent/progress` | POST | 查询任务进度 |
| `/api/agent/permission/confirm` | POST | 确认权限 |
| `/api/agent/reset` | POST | 重置 Agent 状态 |

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


## 记忆库系统

基于向量检索的长期记忆系统，支持:

- **语义搜索**: 通过向量相似度检索相关记忆
- **重排序**: 使用 reranker 模型优化排序结果
- **自动摘要**: 使用 LLM 生成记忆摘要

### 配置

在 `backend/config/config.py` 中配置:

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

在 `backend/config/provider_infos/` 目录下添加新的提供商配置 JSON 文件:

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

## 开发说明

### 前端开发

```bash
cd frontend

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview

# 代码检查
npm run lint
```

### 后端开发

```bash
cd backend

# 启动服务
python -m backend.main

# 或使用 uvicorn
uvicorn api.agent_api:app --reload
```

### 日志

后端日志文件保存在 `backend/logs/`
