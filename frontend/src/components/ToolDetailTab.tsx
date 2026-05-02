import React, { useMemo } from 'react';
import { Wrench, CheckCircle, Loader, Clock, FileCode } from 'lucide-react';
import type { FunctionCallContent } from '../types';
import { parseToolParams, getLanguageFromPath, isSpecialTool } from '../utils/streamParser';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ToolDetailTabProps {
  toolCall: FunctionCallContent;
  isStreaming?: boolean;
}

export const ToolDetailTab: React.FC<ToolDetailTabProps> = ({ toolCall, isStreaming = false }) => {
  // 检查是否是特殊工具
  const isSpecial = useMemo(() => isSpecialTool(toolCall.name), [toolCall.name]);

  // 解析参数（支持流式不完整 JSON）
  const parsedParams = useMemo(() => 
    parseToolParams(toolCall.params), 
    [toolCall.params]
  );

  // 获取文件路径
  const filePath = useMemo(() => {
    return String(parsedParams.file_path || parsedParams.path || '');
  }, [parsedParams]);

  // 获取代码内容
  const codeContent = useMemo(() => {
    return String(
      parsedParams.content || 
      parsedParams.file_content || 
      parsedParams.new_text || 
      parsedParams.new_str || 
      ''
    );
  }, [parsedParams]);

  // 获取原始文本（用于 StrReplace）
  const originalText = useMemo(() => {
    return String(parsedParams.original_text || parsedParams.old_str || '');
  }, [parsedParams]);

  // 获取语言
  const language = useMemo(() => getLanguageFromPath(filePath), [filePath]);

  // 获取状态图标
  const getStatusIcon = () => {
    if (isStreaming) {
      return <Loader size={16} className="spinning" />;
    }
    if (toolCall.result !== undefined) {
      return <CheckCircle size={16} className="status-success" />;
    }
    return <Clock size={16} className="status-pending" />;
  };

  // 渲染特殊工具的代码块
  const renderSpecialToolContent = () => {
    const isReplaceType = toolCall.name.toLowerCase().includes('replace');

    return (
      <div className="special-tool-content">
        {/* 文件路径 */}
        {filePath && (
          <div className="file-path-bar">
            <FileCode size={14} />
            <span className="file-path">{filePath}</span>
          </div>
        )}

        {/* 替换工具显示原始文本 */}
        {isReplaceType && originalText && (
          <div className="code-section">
            <div className="code-section-header original">
              <span>原始内容</span>
            </div>
            <SyntaxHighlighter
              style={oneDark}
              language={language}
              customStyle={{
                margin: 0,
                borderRadius: '0 0 8px 8px',
                background: '#1a1a1a',
                padding: '12px',
                fontSize: '13px',
              }}
            >
              {originalText}
            </SyntaxHighlighter>
          </div>
        )}

        {/* 代码内容 */}
        {(codeContent || isStreaming) && (
          <div className="code-section">
            <div className="code-section-header new">
              <span>{isReplaceType ? '新内容' : '内容'}</span>
              {isStreaming && <span className="streaming-badge">写入中...</span>}
            </div>
            <div className={`code-content-wrapper ${isStreaming ? 'streaming' : ''}`}>
              <SyntaxHighlighter
                style={oneDark}
                language={language}
                customStyle={{
                  margin: 0,
                  borderRadius: '0 0 8px 8px',
                  background: '#1a1a1a',
                  padding: '12px',
                  fontSize: '13px',
                  minHeight: isStreaming ? '100px' : 'auto',
                }}
              >
                {codeContent || ' '}
              </SyntaxHighlighter>
              {isStreaming && <span className="streaming-cursor">|</span>}
            </div>
          </div>
        )}

        {/* 其他参数 */}
        {Object.entries(parsedParams)
          .filter(([key]) => ![
            'content', 'file_content', 'new_text', 'new_str',
            'file_path', 'path', 'original_text', 'old_str'
          ].includes(key))
          .map(([key, value]) => (
            <div key={key} className="param-row">
              <span className="param-label">{key}:</span>
              <span className="param-value">
                {typeof value === 'string' ? value : JSON.stringify(value)}
              </span>
            </div>
          ))
        }
      </div>
    );
  };

  // 渲染普通工具参数
  const renderNormalParams = () => {
    const paramsStr = typeof toolCall.params === 'string' 
      ? toolCall.params 
      : JSON.stringify(toolCall.params, null, 2);

    return (
      <pre className={`code-block ${isStreaming ? 'streaming' : ''}`}>
        <code>{paramsStr}</code>
        {isStreaming && <span className="streaming-cursor">|</span>}
      </pre>
    );
  };

  // 渲染结果内容
  const renderResult = () => {
    if (toolCall.result === undefined) {
      return (
        <div className="result-pending">
          <Clock size={16} />
          <span>等待执行结果...</span>
        </div>
      );
    }

    return (
      <pre className="code-block result">
        <code>{toolCall.result}</code>
      </pre>
    );
  };

  return (
    <div className="tool-detail-tab">
      {/* 工具头部 */}
      <div className="tool-detail-header">
        <div className="tool-info">
          <Wrench size={18} />
          <span className="tool-name">{toolCall.name}</span>
          {getStatusIcon()}
        </div>
        <div className="tool-id">ID: {toolCall.id}</div>
      </div>

      {/* 特殊工具 - 代码块渲染 */}
      {isSpecial ? (
        <div className="tool-detail-section">
          {renderSpecialToolContent()}
        </div>
      ) : (
        /* 普通工具 - 参数和结果 */
        <>
          <div className="tool-detail-section">
            <div className="section-title">参数</div>
            <div className="section-content">
              {renderNormalParams()}
            </div>
          </div>
          <div className="tool-detail-section">
            <div className="section-title">执行结果</div>
            <div className="section-content">
              {renderResult()}
            </div>
          </div>
        </>
      )}

      {/* 特殊工具的执行结果 */}
      {isSpecial && toolCall.result !== undefined && (
        <div className="tool-detail-section">
          <div className="section-title">执行结果</div>
          <div className="section-content">
            {renderResult()}
          </div>
        </div>
      )}
    </div>
  );
};
