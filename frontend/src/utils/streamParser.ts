/**
 * 流式 JSON 解析工具
 * 用于从不完整的 JSON 字符串中提取部分数据
 */

export interface ParsedToolParams {
  file_path?: string;
  content?: string;
  original_text?: string;
  new_text?: string;
  // 其他可能的字段
  [key: string]: unknown;
}

/**
 * 尝试从可能不完整的 JSON 字符串中提取字段值
 * @param jsonStr 可能不完整的 JSON 字符串
 * @param fieldName 要提取的字段名
 * @returns 字段值或 undefined
 */
export function extractFieldFromPartialJson(jsonStr: string, fieldName: string): string | undefined {
  // 尝试匹配 "fieldName": "value" 或 "fieldName": "value（未闭合）
  const patterns = [
    // 完整的字符串值
    new RegExp(`"${fieldName}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"`, 's'),
    // 未闭合的字符串值（流式传输中）
    new RegExp(`"${fieldName}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)$`, 's'),
  ];

  for (const pattern of patterns) {
    const match = jsonStr.match(pattern);
    if (match) {
      // 处理转义字符
      return unescapeJsonString(match[1]);
    }
  }

  return undefined;
}

/**
 * 反转义 JSON 字符串中的转义字符
 */
function unescapeJsonString(str: string): string {
  return str
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '\r')
    .replace(/\\t/g, '\t')
    .replace(/\\"/g, '"')
    .replace(/\\\\/g, '\\');
}

/**
 * 从工具参数中提取文件路径和内容
 * 支持不完整的 JSON 字符串
 */
export function parseToolParams(params: string | Record<string, unknown>): ParsedToolParams {
  // 如果已经是对象，直接返回
  if (typeof params === 'object' && params !== null) {
    return params as ParsedToolParams;
  }

  const result: ParsedToolParams = {};
  const jsonStr = params as string;

  // 首先尝试完整解析
  try {
    return JSON.parse(jsonStr) as ParsedToolParams;
  } catch {
    // 解析失败，使用流式提取
  }

  // 提取常见字段
  const fields = ['file_path', 'path', 'content', 'file_content', 'new_text', 'original_text', 'old_str', 'new_str'];
  
  for (const field of fields) {
    const value = extractFieldFromPartialJson(jsonStr, field);
    if (value !== undefined) {
      result[field] = value;
    }
  }

  return result;
}

/**
 * 检测文件扩展名并返回对应的语言标识
 * 注意：Markdown 文件返回 'text' 以避免嵌套代码块解析问题
 */
export function getLanguageFromPath(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase() || '';
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'jsx',
    'ts': 'typescript',
    'tsx': 'tsx',
    'py': 'python',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
    'cs': 'csharp',
    'go': 'go',
    'rs': 'rust',
    'rb': 'ruby',
    'php': 'php',
    'swift': 'swift',
    'kt': 'kotlin',
    'scala': 'scala',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'less': 'less',
    'json': 'json',
    'xml': 'xml',
    'yaml': 'yaml',
    'yml': 'yaml',
    'md': 'text',       // Markdown 使用纯文本避免嵌套解析问题
    'markdown': 'text', // 同上
    'sql': 'sql',
    'sh': 'bash',
    'bash': 'bash',
    'zsh': 'bash',
    'ps1': 'powershell',
    'dockerfile': 'dockerfile',
  };
  return languageMap[ext] || ext || 'text';
}

/**
 * 检查是否是特殊工具（需要代码块渲染）
 */
export function isSpecialTool(toolName: string): boolean {
  const specialTools = [
    'WriteFile', 'write_file', 'CreateFile', 'create_file',
    'StrReplace', 'str_replace', 'search_replace',
    'EditFile', 'edit_file'
  ];
  return specialTools.some(name => 
    toolName.toLowerCase().includes(name.toLowerCase())
  );
}
