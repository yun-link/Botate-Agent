import React from 'react';
import { Lightbulb, Wrench, ChevronRight, CheckCircle, Loader } from 'lucide-react';
import type { ProgressItem, FunctionCallContent } from '../types';

interface ProgressTabProps {
  items: ProgressItem[];
  onToolClick: (toolCall: FunctionCallContent) => void;
}

export const ProgressTab: React.FC<ProgressTabProps> = ({ items, onToolClick }) => {
  if (items.length === 0) {
    return (
      <div className="progress-empty">
        <p>暂无执行记录</p>
      </div>
    );
  }

  return (
    <div className="progress-tab">
      <div className="progress-list">
        {items.map((item) => (
          <div
            key={item.id}
            className={`progress-item ${item.type} ${item.isStreaming ? 'streaming' : ''}`}
            onClick={() => {
              if (item.type === 'toolCall' && item.toolCall) {
                onToolClick(item.toolCall);
              }
            }}
            style={{ cursor: item.type === 'toolCall' ? 'pointer' : 'default' }}
          >
            <div className="progress-item-icon">
              {item.type === 'reasoning' ? (
                <Lightbulb size={16} />
              ) : (
                <Wrench size={16} />
              )}
            </div>
            <div className="progress-item-content">
              <div className="progress-item-title">
                {item.type === 'reasoning' ? (
                  item.isStreaming ? '思考中...' : '深度思考'
                ) : (
                  item.toolCall?.name || '工具调用'
                )}
              </div>
              {item.type === 'reasoning' && item.content && (
                <div className="progress-item-preview">
                  {item.content.slice(0, 100)}
                  {item.content.length > 100 && '...'}
                </div>
              )}
              {item.type === 'toolCall' && item.toolCall && (
                <div className="progress-item-status">
                  {item.toolCall.result !== undefined ? (
                    <span className="status-complete">
                      <CheckCircle size={12} /> 已完成
                    </span>
                  ) : (
                    <span className="status-running">
                      <Loader size={12} className="spinning" /> 执行中
                    </span>
                  )}
                </div>
              )}
            </div>
            {item.type === 'toolCall' && (
              <div className="progress-item-arrow">
                <ChevronRight size={16} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
