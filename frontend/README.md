# Frontend 前端

一个基于 React 的现代化聊天界面，用于 Botate-Agent 系统，支持实时流式响应、多模态输入，并与后端 Agent API 无缝集成。

## 技术栈

- **React 19** - UI 框架
- **TypeScript** - 类型安全
- **Vite 8** - 构建工具和开发服务器
- **Axios** - HTTP 客户端
- **lucide-react** - 图标库
- **ESLint** - 代码检查

## 功能特性

- 💬 实时聊天界面，支持流式响应
- 🧠 显示助手的推理过程
- 🔧 工具调用可视化与执行
- 📎 支持多模态输入（文本、图片、视频、音频、文件）
- 🔄 自动重连和进度流式传输
- 🎨 简洁现代的 UI 设计

## 快速开始

### 前置要求

- Node.js 20+
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

启动开发服务器，访问地址：`http://localhost:5173`

### 构建生产版本

```bash
npm run build
```

构建产物输出到 `dist` 目录。

### 预览生产版本

```bash
npm run preview
```

### 代码检查

```bash
npm run lint
```

运行 ESLint 检查代码质量。

## 项目结构

```
frontend/
├── src/
│   ├── components/       # React 组件
│   │   ├── AssistantMessage.tsx
│   │   ├── ChatInput.tsx
│   │   ├── DetailPanel.tsx
│   │   ├── EventBar.tsx
│   │   ├── ReasoningBlock.tsx
│   │   ├── ToolCallBlock.tsx
│   │   ├── UserMessage.tsx
│   │   └── index.ts
│   ├── services/         # API 服务
│   │   └── api.ts        # 后端 API 集成
│   ├── types/            # TypeScript 类型定义
│   │   └── index.ts
│   ├── assets/           # 静态资源
│   ├── App.tsx           # 主应用组件
│   ├── App.css           # 应用样式
│   ├── main.tsx          # 入口文件
│   └── index.css         # 全局样式
├── public/               # 公共静态文件
├── index.html            # HTML 模板
├── vite.config.ts        # Vite 配置
├── tsconfig.json         # TypeScript 配置
├── eslint.config.js      # ESLint 配置
└── package.json          # 依赖配置
```

## API 集成

前端通过 REST API 和 Server-Sent Events (SSE) 与后端通信：

### 接口列表

| 接口地址 | 方法 | 说明 |
|----------|------|------|
| `/api/agent/call` | POST | 发送消息到 Agent（SSE 流式） |
| `/api/agent/messages` | GET | 获取消息历史 |
| `/api/agent/progress` | GET | 获取进度流（SSE 流式） |
| `/api/agent/permission/confirm` | POST | 确认权限 |
| `/api/agent/reset` | POST | 重置 Agent 状态 |

### 默认配置

API 基础 URL 配置为 `http://localhost:8000`。如需修改，请编辑 `src/services/api.ts` 中的 `API_BASE_URL`。

## 消息类型

### 流式数据块

前端处理多种流式数据块类型：

- `reasoning` - 助手的推理/思考过程
- `answer` - 最终文本回复
- `function_call` - 工具/函数调用请求
- `event` - 系统事件（任务开始、完成等）
- `error` - 错误消息

### 输入内容类型

- `text` - 纯文本内容
- `image` - 图片文件或 URL
- `video` - 视频文件或 URL
- `audio` - 音频文件
- `file` - 通用文件附件

## 组件架构

### 主要组件

- **App** - 根组件，管理聊天状态和流式传输
- **ChatInput** - 消息输入框，支持文件附件
- **UserMessage** - 渲染用户消息
- **AssistantMessage** - 渲染助手消息（包含推理、工具调用）
- **ReasoningBlock** - 显示推理内容
- **ToolCallBlock** - 显示和处理工具调用

### 状态管理

- `messages` - 消息历史
- `currentBlocks` - 当前流式消息块
- `isLoading` - 加载状态
- `isStreaming` - 流式传输状态

## 开发说明

### React 编译器

默认未启用 React 编译器，因为它会影响开发和构建性能。如需启用，请参阅 [React 官方文档](https://react.dev/learn/react-compiler/installation)。

### ESLint 配置

项目使用 TypeScript ESLint 及推荐规则。如需更严格的类型检查，可启用 `tseslint.configs.recommendedTypeChecked` 或 `tseslint.configs.strictTypeChecked`。

## 后端要求

前端需要后端服务器运行在 `http://localhost:8000`。更多后端详情请参阅 [后端文档](../backend/README.md)。

## 许可证

MIT
