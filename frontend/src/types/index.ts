/**
 * 消息内容类型定义
 */

// 基础内容类型
export interface TextContent {
  content_type: 'text';
  content: string;
}

export interface ImageContent {
  content_type: 'image';
  type: 'file' | 'url';
  content: string;
}

export interface VideoContent {
  content_type: 'video';
  type: 'file' | 'url';
  content: string;
}

export interface AudioContent {
  content_type: 'audio';
  type: 'file';
  content: string;
}

export type InputContentType = TextContent | ImageContent | VideoContent | AudioContent | string;

// 消息类型
export interface Message {
  role: 'user' | 'assistant' | 'tool';
  content: InputContentType | InputContentType[];
  reasoning_content?: string;
  tool_calls?: FunctionCallContent[];
  timestamp: string;
  message_id: string;
}

// 函数调用内容
export interface FunctionCallContent {
  type: 'function_call';
  name: string;
  params: string | Record<string, unknown>;
  id: string;
  index: number;
  result?: string;
}

// 流式响应块类型
export interface AnswerChunk {
  type: 'answer';
  content: string;
}

export interface ReasoningChunk {
  type: 'reasoning';
  content: string;
}

export interface FunctionCallChunk {
  type: 'function_call';
  name: string;
  params: string | Record<string, unknown>;
  id: string;
  index: number;
  result?: string;
}

export interface EventChunk {
  type: 'event';
  event: string;
  tool_name?: string;
  reason?: string;
  timestamp?: string;
}

export interface ErrorChunk {
  type: 'error';
  message: string;
  timestamp?: string;
}

export type StreamChunk = AnswerChunk | ReasoningChunk | FunctionCallChunk | EventChunk | ErrorChunk;

// 权限确认类型
export interface PermissionDeniedData {
  type: 'event';
  event: 'permission_denied';
  tool_name: string;
  reason: string;
  timestamp?: string;
}

export interface PermissionConfirmationData {
  type: 'event';
  event: 'permission_confirmation';
  confirmation_id: string;
  allowed: boolean;
  timestamp?: string;
}

// 事件类型
export type EventType = 
  | 'task_started'
  | 'task_completed'
  | 'answer_begin'
  | 'reasoning_begin'
  | 'function_call_info'
  | 'round_end'
  | 'permission_denied'
  | 'permission_confirmation'
  | 'stream_end';

// 视窗状态
export interface PanelState {
  isOpen: boolean;
  title: string;
  content: React.ReactNode;
  eventData?: EventChunk;
}

// 权限请求状态
export interface PermissionRequest {
  tool_name: string;
  reason: string;
  confirmation_id: string;
  timestamp: string;
}
