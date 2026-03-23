import axios from 'axios';
import type { Message, InputContentType, StreamChunk } from '../types';

const API_BASE_URL = 'http://localhost:8000';

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 调用Agent（SSE流式响应）
export async function callAgent(
  contents: InputContentType[],
  onChunk: (chunk: StreamChunk) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/agent/call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ contents }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6)) as StreamChunk;
            onChunk(data);
            
            if (data.type === 'event' && data.event === 'task_completed') {
              onComplete?.();
              return;
            }
            if (data.type === 'error') {
              onError?.(new Error((data as StreamChunk & { message: string }).message));
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', line, e);
          }
        }
      }
    }

    onComplete?.();
  } catch (error) {
    onError?.(error as Error);
  }
}

// 获取消息列表
export async function getMessages(): Promise<{ messages: Message[]; is_running: boolean }> {
  const response = await apiClient.get('/api/agent/messages');
  return response.data;
}

// 获取进度（SSE流式响应）
export async function getProgress(
  onChunk: (chunk: StreamChunk) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/agent/progress`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6)) as StreamChunk;
            onChunk(data);
            
            if (data.type === 'event' && data.event === 'stream_end') {
              onComplete?.();
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', line, e);
          }
        }
      }
    }

    onComplete?.();
  } catch (error) {
    onError?.(error as Error);
  }
}

// 确认权限
export async function confirmPermission(allowed: boolean): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post('/api/agent/permission/confirm', { allowed });
  return response.data;
}

// 重置Agent
export async function resetAgent(): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post('/api/agent/reset');
  return response.data;
}

// 上传文件（转换为base64）
export async function uploadFile(file: File): Promise<{ type: 'image' | 'video' | 'audio' | 'file'; content: string; name: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const type = getFileType(file);
      resolve({
        type,
        content: result,
        name: file.name,
      });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// 获取文件类型
function getFileType(file: File): 'image' | 'video' | 'audio' | 'file' {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type.startsWith('video/')) return 'video';
  if (file.type.startsWith('audio/')) return 'audio';
  return 'file';
}
