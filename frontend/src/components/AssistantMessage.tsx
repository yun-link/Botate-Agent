import React, { useState, useEffect } from 'react';
import { Copy, Check } from 'lucide-react';
import { ReasoningBlock } from './ReasoningBlock';
import { ToolCallBlock } from './ToolCallBlock';
<<<<<<< HEAD
import { MarkdownRenderer } from './MarkdownRenderer';
=======
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
import type { FunctionCallContent } from '../types';

interface AssistantMessageProps {
  content: string;
  reasoningContent?: string;
  toolCalls?: FunctionCallContent[];
  isStreaming?: boolean;
  permissionDenied?: boolean;
  permissionReason?: string;
<<<<<<< HEAD
  onToolClick?: (toolCall: FunctionCallContent) => void;
=======
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({
  content,
  reasoningContent,
  toolCalls,
  isStreaming = false,
  permissionDenied = false,
  permissionReason,
<<<<<<< HEAD
  onToolClick,
=======
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
}) => {
  const [copied, setCopied] = React.useState(false);
  const [, setDisplayedContent] = useState('');

  // 流式输出效果 - 只在流式模式下使用，且只追加新内容
  useEffect(() => {
    if (!isStreaming) {
      setDisplayedContent(content);
      return;
    }

    // 流式模式下，直接显示完整内容（因为内容是通过handleStreamChunk逐步累积的）
    setDisplayedContent(content);
  }, [content, isStreaming]);

  // 复制文本
  const handleCopy = async () => {
    if (content) {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="assistant-message">
      {/* 深度思考内容 */}
      {reasoningContent && (
        <div className="reasoning-container">
          <ReasoningBlock 
            content={reasoningContent} 
            isStreaming={isStreaming}
          />
        </div>
      )}

      {/* 工具调用展示 */}
      {toolCalls && toolCalls.length > 0 && (
        <div className="tool-calls-container">
          {toolCalls.map((toolCall) => (
            <ToolCallBlock 
              key={toolCall.id} 
              toolCall={toolCall}
              permissionDenied={permissionDenied}
              permissionReason={permissionReason}
<<<<<<< HEAD
              onClick={onToolClick}
=======
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
            />
          ))}
        </div>
      )}

<<<<<<< HEAD
      {/* 回答内容 - 使用 Markdown 渲染 */}
      {content && (
        <div className="answer-container">
          <div className="answer-content">
            <MarkdownRenderer 
              content={content} 
              isStreaming={isStreaming} 
            />
=======
      {/* 回答内容 */}
      {content && (
        <div className="answer-container">
          <div className="answer-content">
            <div className="answer-text">{content}</div>
>>>>>>> 3b6207bf3905d3834c0f1280877b0f8e91171b1d
          </div>
          <div className="answer-actions">
            <button 
              className="copy-button" 
              onClick={handleCopy}
              title="复制消息"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
