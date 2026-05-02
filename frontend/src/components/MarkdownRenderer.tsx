import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
}

// 复制按钮组件
const CopyButton: React.FC<{ code: string }> = ({ code }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button className="code-copy-btn" onClick={handleCopy} title="复制代码">
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  isStreaming = false,
}) => {
  return (
    <div className={`markdown-content ${isStreaming ? 'streaming' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 代码块
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');
            const isInline = !match && !className;
            
            if (isInline) {
              return (
                <code className="inline-code" {...props}>
                  {children}
                </code>
              );
            }

            return (
              <div className="code-block-wrapper">
                <div className="code-block-header">
                  <span className="code-language">{match ? match[1] : 'code'}</span>
                  <CopyButton code={codeString} />
                </div>
                <SyntaxHighlighter
                  style={oneDark}
                  language={match ? match[1] : 'text'}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    borderRadius: '8px',
                    background: '#1a1a1a',
                    padding: '12px',
                  }}
                >
                  {codeString}
                </SyntaxHighlighter>
              </div>
            );
          },
          // 段落
          p({ children }) {
            return <p className="md-paragraph">{children}</p>;
          },
          // 标题
          h1({ children }) {
            return <h1 className="md-heading md-h1">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="md-heading md-h2">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="md-heading md-h3">{children}</h3>;
          },
          // 列表
          ul({ children }) {
            return <ul className="md-list md-ul">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="md-list md-ol">{children}</ol>;
          },
          li({ children }) {
            return <li className="md-list-item">{children}</li>;
          },
          // 引用
          blockquote({ children }) {
            return <blockquote className="md-blockquote">{children}</blockquote>;
          },
          // 链接
          a({ href, children }) {
            return (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer"
                className="md-link"
              >
                {children}
              </a>
            );
          },
          // 表格
          table({ children }) {
            return (
              <div className="md-table-wrapper">
                <table className="md-table">{children}</table>
              </div>
            );
          },
          // 水平线
          hr() {
            return <hr className="md-hr" />;
          },
          // 强调
          strong({ children }) {
            return <strong className="md-strong">{children}</strong>;
          },
          em({ children }) {
            return <em className="md-em">{children}</em>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && <span className="typing-cursor">▊</span>}
    </div>
  );
};
