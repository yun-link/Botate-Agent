import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Wrench, CheckCircle, XCircle} from 'lucide-react';
import type { FunctionCallContent } from '../types';

interface ToolCallBlockProps {
  toolCall: FunctionCallContent;
  permissionDenied?: boolean;
  permissionReason?: string;
}

export const ToolCallBlock: React.FC<ToolCallBlockProps> = ({ 
  toolCall, 
  permissionDenied = false,
}) => {
  // 当权限被拒绝时，自动展开
  const [isExpanded, setIsExpanded] = useState(permissionDenied);

  useEffect(() => {
    if (permissionDenied) {
      setIsExpanded(true);
    }
  }, [permissionDenied]);

  const toggleExpand = () => {
    if (!permissionDenied) {
      setIsExpanded(!isExpanded);
    }
  };

  // 格式化参数
  const formatParams = () => {
    if (typeof toolCall.params === 'string') {
      try {
        return JSON.stringify(JSON.parse(toolCall.params), null, 2);
      } catch {
        return toolCall.params;
      }
    }
    return JSON.stringify(toolCall.params, null, 2);
  };

  // 格式化结果
  const formatResult = () => {
    if (toolCall.result === undefined) {
      return '';
    }
    if (typeof toolCall.result === 'string') {
      return toolCall.result;
    }
    // 如果是对象，尝试格式化
    try {
      return JSON.stringify(toolCall.result, null, 2);
    } catch {
      return String(toolCall.result);
    }
  };

  // 获取状态图标
  const getStatusIcon = () => {
    if (toolCall.result !== undefined) {
      return <CheckCircle size={14} className="status-success" />;
    }
    return <XCircle size={14} className="status-pending" />;
  };

  return (
    <div className="tool-call-block">
      <div 
        className="tool-call-header" 
        onClick={toggleExpand}
        role="button"
        tabIndex={0}
      >
        <div className="tool-call-title">
          <Wrench size={14} className="tool-icon" />
          <span className="tool-name">{toolCall.name}</span>
          {getStatusIcon()}
        </div>
        <div className="tool-call-toggle">
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>
      
      {isExpanded && (
        <div className="tool-call-content">
          <div className="tool-call-section">
            <div className="section-label">参数:</div>
            <pre className="code-block">
              <code>{formatParams()}</code>
            </pre>
          </div>
          
          {toolCall.result !== undefined && (
            <div className="tool-call-section">
              <div className="section-label">结果:</div>
              <pre className="code-block result">
                <code>{formatResult()}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
