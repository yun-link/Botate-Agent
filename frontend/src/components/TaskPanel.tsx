import React from 'react';
import { X } from 'lucide-react';
import type { TabInfo, ProgressItem, FunctionCallContent } from '../types';
import { ProgressTab } from './ProgressTab';
import { ToolDetailTab } from './ToolDetailTab';

interface TaskPanelProps {
  isOpen: boolean;
  tabs: TabInfo[];
  activeTabId: string;
  progressItems: ProgressItem[];
  onClose: () => void;
  onTabChange: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
  onToolClick: (toolCall: FunctionCallContent) => void;
}

export const TaskPanel: React.FC<TaskPanelProps> = ({
  isOpen,
  tabs,
  activeTabId,
  progressItems,
  onClose,
  onTabChange,
  onTabClose,
  onToolClick,
}) => {
  if (!isOpen) return null;

  const activeTab = tabs.find(t => t.id === activeTabId);

  return (
    <div className="task-panel">
      {/* 面板头部 */}
      <div className="panel-header">
        <div className="panel-tabs">
          {tabs.map(tab => (
            <div
              key={tab.id}
              className={`panel-tab ${tab.id === activeTabId ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              <span className="tab-title">{tab.title}</span>
              {tab.closable && (
                <button
                  className="tab-close-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onTabClose(tab.id);
                  }}
                >
                  <X size={12} />
                </button>
              )}
            </div>
          ))}
        </div>
        <button className="panel-close-btn" onClick={onClose}>
          <X size={20} />
        </button>
      </div>

      {/* 面板内容 */}
      <div className="panel-body">
        {activeTab?.type === 'progress' && (
          <ProgressTab 
            items={progressItems} 
            onToolClick={onToolClick}
          />
        )}
        {activeTab?.type === 'toolDetail' && activeTab.toolCall && (
          <ToolDetailTab 
            toolCall={activeTab.toolCall} 
            isStreaming={activeTab.isStreaming}
          />
        )}
      </div>
    </div>
  );
};
