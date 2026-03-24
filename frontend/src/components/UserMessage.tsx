import React, { useCallback } from 'react';
import { Copy, Check } from 'lucide-react';
import type { Message } from '../types';

interface UserMessageProps {
  message: Message;
}

export const UserMessage: React.FC<UserMessageProps> = ({ message }) => {
  const [copied, setCopied] = React.useState(false);

  // 提取文本内容
  const getTextContent = useCallback((): string => {
    if (typeof message.content === 'string') {
      return message.content;
    }
    const contents = Array.isArray(message.content) ? message.content : [message.content];
    return contents
      .filter((item) => 
        typeof item === 'object' && item !== null && 'content_type' in item && item.content_type === 'text'
      )
      .map(item => (item as { content: string }).content)
      .join('\n');
  }, [message.content]);

  // 复制文本
  const handleCopy = useCallback(async () => {
    const text = getTextContent();
    if (text) {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [getTextContent]);

  const textContent = getTextContent();

  return (
    <div className="user-message">
      {/* 消息内容区域 */}
      {textContent && (
        <div className="user-message-content">
          <div className="message-content-wrapper">
            <div className="message-bubble">
              <div className="message-text">{textContent}</div>
            </div>
          </div>
          <div className="message-actions">
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
