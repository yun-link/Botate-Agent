import React, { useState, useRef, useCallback } from 'react';
import { ArrowUp } from 'lucide-react';
import type { InputContentType } from '../types';

interface ChatInputProps {
  onSend: (contents: InputContentType[]) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ 
  onSend, 
  isLoading = false,
  disabled = false 
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整 textarea 高度
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, []);

  // 处理文本输入
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    adjustTextareaHeight();
  };

  // 发送消息
  const handleSend = useCallback(async () => {
    if (disabled || isLoading) return;
    if (!text.trim()) return;

    const contents: InputContentType[] = [];

    // 添加文本内容
    contents.push({
      content_type: 'text',
      content: text.trim(),
    });

    onSend(contents);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [text, onSend, disabled, isLoading]);

  // 处理键盘事件
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <div className="chat-input-container">
      {/* 主输入区域 */}
      <div className="input-main-area">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          placeholder="输入消息..."
          rows={1}
        />
      </div>

      {/* 底部工具栏 */}
      <div className="input-toolbar">
        {/* 左侧：空白占位 */}
        <div className="toolbar-left"></div>

        {/* 右侧：发送按钮 */}
        <button 
          className="icon-btn send-btn"
          onClick={handleSend}
          disabled={disabled || isLoading || !text.trim()}
        >
          <ArrowUp size={20} />
        </button>
      </div>
    </div>
  );
};
