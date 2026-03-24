import React, { useState, useRef, useCallback, useEffect } from 'react';
import { UserMessage, AssistantMessage, ChatInput, PermissionConfirm } from './components';
import { callAgent, getMessages, getProgress, resetAgent, confirmPermission } from './services/api';
import type { Message, StreamChunk, FunctionCallContent, InputContentType, PermissionRequest } from './types';
import './App.css';

// 消息块类型：用于按顺序渲染推理、工具调用和回答
type MessageBlock = 
  | { type: 'reasoning'; content: string; isStreaming: boolean }
  | { type: 'toolCall'; toolCall: FunctionCallContent; permissionDenied?: boolean; permissionReason?: string }
  | { type: 'answer'; content: string; isStreaming: boolean };

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [, setIsStreaming] = useState(false);
  // 当前流式消息的块列表（按顺序）
  const [currentBlocks, setCurrentBlocks] = useState<MessageBlock[]>([]);
  // 待确认的权限请求
  const [pendingPermission, setPendingPermission] = useState<PermissionRequest | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 加载历史消息
  const loadMessages = useCallback(async () => {
    try {
      const data = await getMessages();
      setMessages(data.messages);
      return data.is_running;
    } catch (error) {
      console.error('Failed to load messages:', error);
      return false;
    }
  }, []);

  // 初始加载
  useEffect(() => {
    loadMessages().then(isRunning => {
      if (isRunning) {
        connectProgressStream();
      }
    });
  }, []);

  // 自动滚动
  useEffect(() => {
    scrollToBottom();
  }, [messages, currentBlocks, scrollToBottom]);

  // 连接进度流
  const connectProgressStream = useCallback(() => {
    setIsStreaming(true);
    setIsLoading(true);
    
    getProgress(
      (chunk) => {
        handleStreamChunk(chunk);
      },
      (error) => {
        console.error('Progress stream error:', error);
        setIsStreaming(false);
        setIsLoading(false);
        setCurrentBlocks([]);
        loadMessages();
      },
      () => {
        setIsStreaming(false);
        setIsLoading(false);
        setCurrentBlocks([]);
        loadMessages();
      }
    );
  }, [loadMessages]);

  // 处理流式数据块 - 按顺序添加块
  const handleStreamChunk = useCallback((chunk: StreamChunk) => {
    switch (chunk.type) {
      case 'reasoning':
        setCurrentBlocks(prev => {
          // 只有当最后一个块是推理块时才追加，否则创建新块
          if (prev.length > 0 && prev[prev.length - 1].type === 'reasoning') {
            // 更新最后一个推理块
            const newBlocks = [...prev];
            const lastBlock = newBlocks[newBlocks.length - 1] as { type: 'reasoning'; content: string; isStreaming: boolean };
            newBlocks[newBlocks.length - 1] = {
              type: 'reasoning',
              content: lastBlock.content + chunk.content,
              isStreaming: true,
            };
            return newBlocks;
          } else {
            // 创建新的推理块
            return [...prev, { type: 'reasoning', content: chunk.content, isStreaming: true }];
          }
        });
        break;
        
      case 'function_call':
        const fc = chunk as FunctionCallContent;
        setCurrentBlocks(prev => {
          // 查找是否已有相同 ID 的工具调用
          const existingIndex = prev.findIndex(b => b.type === 'toolCall' && (b as any).toolCall.id === fc.id);
          if (existingIndex >= 0) {
            // 更新现有工具调用
            const newBlocks = [...prev];
            const existingBlock = newBlocks[existingIndex] as { type: 'toolCall'; toolCall: FunctionCallContent; permissionDenied?: boolean; permissionReason?: string };
            newBlocks[existingIndex] = { 
              type: 'toolCall', 
              toolCall: fc,
              permissionDenied: existingBlock.permissionDenied,
              permissionReason: existingBlock.permissionReason
            };
            return newBlocks;
          } else {
            // 创建新的工具调用块
            return [...prev, { type: 'toolCall', toolCall: fc }];
          }
        });
        break;
        
      case 'event':
        if (chunk.event === 'permission_denied') {
          const permissionData = chunk as { tool_name?: string; reason?: string };
          const reason = permissionData.reason || '权限不足';
          // 创建权限请求
          const permissionRequest: PermissionRequest = {
            tool_name: permissionData.tool_name || 'unknown',
            reason: reason,
            confirmation_id: `perm_${Date.now()}`,
            timestamp: new Date().toISOString()
          };
          setPendingPermission(permissionRequest);
          
          // 标记最后一个工具调用为权限被拒绝
          setCurrentBlocks(prev => {
            const newBlocks = [...prev];
            // 找到最后一个工具调用块
            for (let i = newBlocks.length - 1; i >= 0; i--) {
              if (newBlocks[i].type === 'toolCall') {
                const existingBlock = newBlocks[i] as { type: 'toolCall'; toolCall: FunctionCallContent; permissionDenied?: boolean; permissionReason?: string };
                newBlocks[i] = { 
                  type: 'toolCall', 
                  toolCall: existingBlock.toolCall,
                  permissionDenied: true,
                  permissionReason: reason
                };
                break;
              }
            }
            return newBlocks;
          });
        }
        break;
        
      case 'answer':
        setCurrentBlocks(prev => {
          // 只有当最后一个块是回答块时才追加，否则创建新块
          if (prev.length > 0 && prev[prev.length - 1].type === 'answer') {
            // 更新最后一个回答块
            const newBlocks = [...prev];
            const lastBlock = newBlocks[newBlocks.length - 1] as { type: 'answer'; content: string; isStreaming: boolean };
            newBlocks[newBlocks.length - 1] = {
              type: 'answer',
              content: lastBlock.content + chunk.content,
              isStreaming: true,
            };
            return newBlocks;
          } else {
            // 创建新的回答块
            return [...prev, { type: 'answer', content: chunk.content, isStreaming: true }];
          }
        });
        break;
    }
  }, []);

  // 发送消息
  const handleSend = useCallback(async (contents: InputContentType[]) => {
    if (isLoading) return;
    if (!contents || contents.length === 0) {
      console.error('Cannot send empty message');
      return;
    }
    
    setIsLoading(true);
    setIsStreaming(true);
    
    // 添加用户消息
    const userMessage: Message = {
      role: 'user',
      content: contents,
      timestamp: new Date().toISOString(),
      message_id: Math.random().toString(36).substring(7),
    };
    setMessages(prev => [...prev, userMessage]);
    
    // 重置当前块列表
    setCurrentBlocks([]);
    
    // 调用 API
    await callAgent(
      contents,
      handleStreamChunk,
      (error) => {
        console.error('Call agent error:', error);
        setIsStreaming(false);
        setIsLoading(false);
        setCurrentBlocks([]);
        loadMessages();
      },
      async () => {
        setIsStreaming(false);
        setIsLoading(false);
        setCurrentBlocks([]);
        await loadMessages();
      }
    );
  }, [isLoading, handleStreamChunk, loadMessages]);

  // 重置对话
  const handleReset = useCallback(async () => {
    try {
      await resetAgent();
      setMessages([]);
      setCurrentBlocks([]);
      setIsStreaming(false);
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to reset:', error);
    }
  }, []);

  // 提取文本内容
  const extractTextContent = (content: Message['content']): string => {
    if (typeof content === 'string') {
      return content;
    } else if (Array.isArray(content)) {
      return content
        .filter(item => typeof item === 'object' && item !== null && 'content_type' in item && item.content_type === 'text')
        .map(item => (item as { content: string }).content)
        .join('\n');
    } else if (typeof content === 'object' && content !== null) {
      const c = content as { content_type?: string; content?: string };
      if (c.content_type === 'text') {
        return c.content || '';
      }
    }
    return '';
  };

  // 处理权限确认
  const handlePermissionConfirm = useCallback(async () => {
    if (!pendingPermission) return;
    
    try {
      await confirmPermission(true);
      setPendingPermission(null);
    } catch (error) {
      console.error('Failed to confirm permission:', error);
    }
  }, [pendingPermission]);

  // 处理权限拒绝
  const handlePermissionDeny = useCallback(async () => {
    if (!pendingPermission) return;
    
    try {
      await confirmPermission(false);
      setPendingPermission(null);
    } catch (error) {
      console.error('Failed to deny permission:', error);
    }
  }, [pendingPermission]);

  return (
    <div className="app">
      {/* 主聊天区域 */}
      <div className="chat-container">
        {/* 顶部栏 */}
        <div className="top-bar">
          <div className="top-bar-content">
            <button className="reset-icon-btn" onClick={handleReset} title="重置对话">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                <path d="M3 3v5h5"/>
              </svg>
            </button>
          </div>
        </div>

        {/* 消息列表 */}
        <div className="messages-container">
          {messages.filter(m => m.role !== 'tool').map((message, index) => {
            const contentText = extractTextContent(message.content);
            const hasReasoning = message.reasoning_content && message.reasoning_content.length > 0;
            const hasToolCalls = message.tool_calls && message.tool_calls.length > 0;
            const hasAnswer = contentText && contentText.length > 0;
            
            // 如果有推理、工具调用或回答，分别渲染
            if (message.role === 'assistant') {
              return (
                <React.Fragment key={message.message_id || index}>
                  {hasReasoning && (
                    <div className="message-wrapper assistant" key={`${message.message_id}-reasoning`}>
                      <div className="message-content">
                        <AssistantMessage
                          content=""
                          reasoningContent={message.reasoning_content}
                          toolCalls={[]}
                          isStreaming={false}
                        />
                      </div>
                    </div>
                  )}
                  {hasToolCalls && (
                    <div className="message-wrapper assistant" key={`${message.message_id}-tools`}>
                      <div className="message-content">
                        <AssistantMessage
                          content=""
                          reasoningContent=""
                          toolCalls={message.tool_calls}
                          isStreaming={false}
                        />
                      </div>
                    </div>
                  )}
                  {hasAnswer && (
                    <div className="message-wrapper assistant" key={`${message.message_id}-answer`}>
                      <div className="message-content">
                        <AssistantMessage
                          content={contentText}
                          reasoningContent=""
                          toolCalls={[]}
                          isStreaming={false}
                        />
                      </div>
                    </div>
                  )}
                  {!hasReasoning && !hasToolCalls && !hasAnswer && (
                    <div 
                      key={message.message_id || index} 
                      className={`message-wrapper ${message.role}`}
                    >
                      <div className="message-content">
                        <AssistantMessage
                          content={contentText}
                          reasoningContent={message.reasoning_content || ''}
                          toolCalls={message.tool_calls || []}
                          isStreaming={false}
                        />
                      </div>
                    </div>
                  )}
                </React.Fragment>
              );
            }
            
            // 用户消息
            return (
              <div 
                key={message.message_id || index} 
                className={`message-wrapper ${message.role}`}
              >
                <div className="message-content">
                  <UserMessage message={message} />
                </div>
              </div>
            );
          })}

          {/* 当前流式消息 - 按顺序渲染块 */}
          {currentBlocks.length > 0 && (
            <div className="message-wrapper assistant">
              <div className="message-content">
                {currentBlocks.map((block, index) => {
                  if (block.type === 'reasoning') {
                    return (
                      <AssistantMessage
                        key={`reasoning-${index}`}
                        content=""
                        reasoningContent={block.content}
                        toolCalls={[]}
                        isStreaming={block.isStreaming}
                      />
                    );
                  } else if (block.type === 'toolCall') {
                    const toolBlock = block as { type: 'toolCall'; toolCall: FunctionCallContent; permissionDenied?: boolean; permissionReason?: string };
                    return (
                      <React.Fragment key={`tool-${block.toolCall.id}`}>
                        <AssistantMessage
                          content=""
                          reasoningContent=""
                          toolCalls={[toolBlock.toolCall]}
                          isStreaming={false}
                          permissionDenied={toolBlock.permissionDenied}
                          permissionReason={toolBlock.permissionReason}
                        />
                        {toolBlock.permissionDenied && toolBlock.permissionReason && pendingPermission && (
                          <PermissionConfirm
                            permissionRequest={pendingPermission}
                            onConfirm={handlePermissionConfirm}
                            onDeny={handlePermissionDeny}
                          />
                        )}
                      </React.Fragment>
                    );
                  } else if (block.type === 'answer') {
                    return (
                      <AssistantMessage
                        key={`answer-${index}`}
                        content={block.content}
                        reasoningContent=""
                        toolCalls={[]}
                        isStreaming={block.isStreaming}
                      />
                    );
                  }
                  return null;
                })}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="input-wrapper">
          <ChatInput 
            onSend={handleSend} 
            isLoading={isLoading}
            disabled={isLoading}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
