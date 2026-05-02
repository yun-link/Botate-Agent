import React from 'react';
import { Wrench, CheckCircle, XCircle, ChevronRight } from 'lucide-react';
import type { FunctionCallContent } from '../types';

interface ToolCallBlockProps {
  toolCall: FunctionCallContent;
  permissionDenied?: boolean;
  permissionReason?: string;
  onClick?: (toolCall: FunctionCallContent) => void;
}

export const ToolCallBlock: React.FC<ToolCallBlockProps> = ({ 
  toolCall, 
  permissionDenied = false,
  onClick,
}) => {
  const handleClick = () => {
    onClick?.(toolCall);
  };

  // 获取状态图标
  const getStatusIcon = () => {
    if (toolCall.result !== undefined) {
      return <CheckCircle size={14} className="status-success" />;
    }
    return <XCircle size={14} className="status-pending" />;
  };

  return (
    <div 
      className={`tool-call-block ${permissionDenied ? 'permission-denied' : ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
    >
      <div className="tool-call-header">
        <div className="tool-call-title">
          <Wrench size={14} className="tool-icon" />
          <span className="tool-name">{toolCall.name}</span>
          {getStatusIcon()}
        </div>
        <div className="tool-call-toggle">
          <ChevronRight size={16} />
        </div>
      </div>
    </div>
  );
};
