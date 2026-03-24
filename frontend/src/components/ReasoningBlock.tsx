import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Lightbulb } from 'lucide-react';

interface ReasoningBlockProps {
  content: string;
  isStreaming?: boolean;
  onComplete?: () => void;
}

export const ReasoningBlock: React.FC<ReasoningBlockProps> = ({ 
  content, 
  isStreaming = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="reasoning-block">
      <div 
        className="reasoning-header" 
        onClick={toggleExpand}
        role="button"
        tabIndex={0}
      >
        <div className="reasoning-title">
          <Lightbulb size={16} className="reasoning-icon" />
          <span>{isStreaming ? '思考中...' : '思考已完成'}</span>
        </div>
        <div className="reasoning-toggle">
          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </div>
      
      {isExpanded && (
        <div className="reasoning-content">
          <div className="reasoning-text">
            {content}
          </div>
        </div>
      )}
    </div>
  );
};
