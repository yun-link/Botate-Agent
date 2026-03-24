import React from 'react';
import { X, Terminal, FileText, Zap, AlertCircle, CheckCircle } from 'lucide-react';
import type { EventChunk, FunctionCallContent } from '../types';

interface DetailPanelProps {
  isOpen: boolean;
  onClose: () => void;
  event?: EventChunk | null;
  toolCall?: FunctionCallContent | null;
  title?: string;
}

export const DetailPanel: React.FC<DetailPanelProps> = ({ 
  isOpen, 
  onClose, 
  event, 
  toolCall,
  title 
}) => {
  if (!isOpen) return null;

  // 获取事件图标
  const getEventIcon = () => {
    if (!event) return <FileText size={20} />;
    
    switch (event.event) {
      case 'task_started':
        return <Zap size={20} />;
      case 'task_completed':
        return <CheckCircle size={20} />;
      case 'answer_begin':
        return <FileText size={20} />;
      case 'reasoning_begin':
        return <Terminal size={20} />;
      case 'function_call_info':
        return <Zap size={20} />;
      case 'round_end':
        return <CheckCircle size={20} />;
      case 'permission_denied':
        return <AlertCircle size={20} />;
      default:
        return <FileText size={20} />;
    }
  };

  // 获取面板标题
  const getPanelTitle = () => {
    if (title) return title;
    if (!event) return '详情';
    
    switch (event.event) {
      case 'task_started':
        return '任务开始';
      case 'task_completed':
        return '任务完成';
      case 'answer_begin':
        return '开始回答';
      case 'reasoning_begin':
        return '开始思考';
      case 'function_call_info':
        return event.tool_name ? `工具调用: ${event.tool_name}` : '工具调用';
      case 'round_end':
        return '轮次结束';
      case 'permission_denied':
        return '权限被拒绝';
      default:
        return event.event;
    }
  };

  // 渲染事件详情
  const renderEventDetails = () => {
    if (!event) return null;

    const details: Record<string, string> = {
      '事件类型': event.event,
    };

    if (event.tool_name) {
      details['工具名称'] = event.tool_name;
    }

    if (event.reason) {
      details['原因'] = event.reason;
    }

    if (event.timestamp) {
      details['时间戳'] = new Date(event.timestamp).toLocaleString();
    }

    return (
      <div className="event-details">
        {Object.entries(details).map(([key, value]) => (
          <div key={key} className="detail-row">
            <span className="detail-label">{key}:</span>
            <span className="detail-value">{value}</span>
          </div>
        ))}
      </div>
    );
  };

  // 渲染工具调用详情
  const renderToolCallDetails = () => {
    if (!toolCall) return null;

    return (
      <div className="tool-call-details">
        <div className="detail-section">
          <div className="section-title">工具名称</div>
          <div className="section-content">{toolCall.name}</div>
        </div>
        
        <div className="detail-section">
          <div className="section-title">参数</div>
          <pre className="code-block">
            <code>
              {typeof toolCall.params === 'string' 
                ? toolCall.params 
                : JSON.stringify(toolCall.params, null, 2)}
            </code>
          </pre>
        </div>

        {toolCall.result !== undefined && (
          <div className="detail-section">
            <div className="section-title">执行结果</div>
            <pre className="code-block result">
              <code>{toolCall.result}</code>
            </pre>
          </div>
        )}

        <div className="detail-section">
          <div className="section-title">调用ID</div>
          <div className="section-content code">{toolCall.id}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="detail-panel">
      <div className="panel-header">
        <div className="panel-title">
          {getEventIcon()}
          <span>{getPanelTitle()}</span>
        </div>
        <button className="close-btn" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
      
      <div className="panel-content">
        {event && renderEventDetails()}
        {toolCall && renderToolCallDetails()}
      </div>
    </div>
  );
};
