import React from 'react';
import { ChevronRight, FileText, Zap, AlertCircle, CheckCircle, Terminal } from 'lucide-react';
import type { EventChunk } from '../types';

interface EventBarProps {
  event: EventChunk;
  onClick?: (event: EventChunk) => void;
  isActive?: boolean;
}

export const EventBar: React.FC<EventBarProps> = ({ event, onClick, isActive = false }) => {
  // 获取事件图标
  const getEventIcon = () => {
    switch (event.event) {
      case 'task_started':
        return <Zap size={16} />;
      case 'task_completed':
        return <CheckCircle size={16} />;
      case 'answer_begin':
        return <FileText size={16} />;
      case 'reasoning_begin':
        return <Terminal size={16} />;
      case 'function_call_info':
        return <Zap size={16} />;
      case 'round_end':
        return <CheckCircle size={16} />;
      case 'permission_denied':
        return <AlertCircle size={16} />;
      default:
        return <FileText size={16} />;
    }
  };

  // 获取事件显示文本
  const getEventText = () => {
    switch (event.event) {
      case 'task_started':
        return '开始任务';
      case 'task_completed':
        return '任务完成';
      case 'answer_begin':
        return '开始回答';
      case 'reasoning_begin':
        return '开始思考';
      case 'function_call_info':
        return event.tool_name ? `调用: ${event.tool_name}` : '调用工具';
      case 'round_end':
        return '轮次结束';
      case 'permission_denied':
        return `权限被拒绝: ${event.tool_name || ''}`;
      case 'permission_confirmation':
        return '权限确认';
      default:
        return event.event;
    }
  };

  // 获取事件样式类
  const getEventClass = () => {
    switch (event.event) {
      case 'task_started':
      case 'answer_begin':
      case 'reasoning_begin':
        return 'event-info';
      case 'task_completed':
      case 'round_end':
        return 'event-success';
      case 'function_call_info':
        return 'event-action';
      case 'permission_denied':
        return 'event-warning';
      default:
        return 'event-default';
    }
  };

  const handleClick = () => {
    onClick?.(event);
  };

  return (
    <div 
      className={`event-bar ${getEventClass()} ${isActive ? 'active' : ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
    >
      <div className="event-icon">
        {getEventIcon()}
      </div>
      <div className="event-text">
        {getEventText()}
      </div>
      <div className="event-arrow">
        <ChevronRight size={16} />
      </div>
    </div>
  );
};
