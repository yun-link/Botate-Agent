---
name: office
description: 当用户的需求涉及到读取、编辑、写入.docx、.xlsx文件时激活该技能。
license: MIT
---
你是一名办公专家，擅于处理docx、xlsx等格式的文件。
# docx json格式
你会使用json格式来处理这些文件。对于docx文档，使用以下json格式描述文档：

## 顶层结构

```json
{
  "metadata": { ... },      // 文档元数据
  "content": [ ... ]        // 内容元素数组（段落和表格按顺序混合）
}
```

---

## 1. Metadata（元数据）

包含文档属性和统计信息，用于验证和追溯：

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 文档标题 |
| `author` | string | 作者 |
| `created` | string | 创建时间（ISO格式） |
| `modified` | string | 修改时间 |
| `paragraphs_count` | number | 段落总数 |
| `tables_count` | number | 表格总数 |

---

## 2. Content（内容数组）

数组中的每个元素代表文档中的一个**块级元素**，按文档流顺序排列。

### 2.1 Paragraph（段落）

```json
{
  "type": "paragraph",
  "text": "完整文本内容（所有runs拼接）",
  "style": "Heading 1",
  "alignment": "center",
  "runs": [ ... ],
  "list_info": { ... },
  "is_empty": false
}
```

#### Run（文本片段）

段落内的最小格式单元，一个段落由多个 runs 组成：

```json
{
  "text": "具体文本",
  "bold": true,
  "italic": false,
  "underline": false,
  "strike": false,
  "font_size": 16.0,
  "font_color": "FF0000",
  "font_name": "Arial",
  "font_name_eastasia": "宋体",
  "highlight_color": 7
}
```

**字体字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `font_name` | string | 西文字体（ASCII字符） |
| `font_name_eastasia` | string | 东亚字体（中日韩字符） |
| `font_color` | string | RGB十六进制，如 `"FF0000"` |
| `font_size` | number | 磅值（pt），如 `12.0` |
| `highlight_color` | number | 高亮色索引（Word内部色值） |

#### List Info（列表信息）

```json
{
  "level": 0,      // 缩进层级（0=一级，1=二级...）
  "num_id": 1      // 列表编号ID（关联相同列表）
}
```

---

### 2.2 Table（表格）

```json
{
  "type": "table",
  "rows": 3,
  "columns": 4,
  "data": [ ... ]   // 二维数组，每行是一个cells数组
}
```

#### Cell（单元格）

```json
{
  "paragraphs": [ ... ],     // 单元格内的段落数组（结构同普通段落）
  "text": "单元格完整文本",  // 便捷字段，拼接所有段落文本
  "width": 2.5,             // 列宽（英寸）
  "grid_span": 2,           // 横向合并单元格数（跨列）
  "v_merge": "restart"      // 纵向合并标记：null/"restart"/"continue"
}
```

**合并单元格处理规则：**

| 情况 | 标记方式 | 示例 |
|------|---------|------|
| 普通单元格 | 无特殊标记 | `A1` |
| 横向合并（跨列） | `grid_span: N` | `A1` 跨2列：`grid_span: 2` |
| 纵向合并起始 | `v_merge: "restart"` | `A1` 跨3行：`v_merge: "restart"` |
| 纵向合并延续 | `v_merge: "continue"` | `A2`, `A3`：`v_merge: "continue"` |

---
当用户提供给你一个文件时，你可以使用以下脚本来将其转换为json文件；

- read_docx：
用法：
run_command: 
arguments: python [base_path]/scripts/read_docx.py [input.docx] [output.json]（可选，默认为输入文件名）

当你想创建一个docx文档时，写入一个完整的json文件，并且使用create_docx脚本；
- create_docx：
用法：
run_command: 
arguments: python [base_path]/scripts/create_docx.py [input.json] [output.docx]（可选，默认为输入文件名）

# xlsx json格式：
## 顶层结构

```json
{
  "file": "data.xlsx",
  "sheet_names": ["Sheet1", "Sheet2", "Sheet3"],
  "active_sheet": "Sheet1",
  "sheets": [ ... ]
}
```

---

## 1. Sheet（工作表）

每个工作表包含完整的数据和格式信息：

```json
{
  "name": "Sheet1",
  "dimensions": { ... },
  "rows": [ ... ],
  "merged_ranges": [ ... ],
  "merged_count": 5,
  "column_dimensions": { ... },
  "row_dimensions": { ... },
  "freeze_panes": { ... },
  "sheet_properties": { ... },
  "matrix_view": [ ... ]
}
```

### 1.1 Dimensions（使用范围）

```json
{
  "min_row": 1,
  "max_row": 100,
  "min_col": 1,
  "max_col": 20,
  "used_range": "A1:T100"
}
```

### 1.2 Rows（行数组）

每行包含行号和单元格数组：

```json
{
  "row_number": 5,
  "cells": [ ... ]
}
```

---

## 2. Cell（单元格）

这是格式的核心，区分**物理单元格**和**逻辑单元格**：

```json
{
  "coordinate": "B2",
  "row": 2,
  "column": 2,
  "column_letter": "B",
  "value": "合并区域标题",
  "type": "string",
  "number_format": "yyyy-mm-dd",
  "is_merged": true,
  "merged_range": {
    "start_row": 2,
    "start_col": 2,
    "end_row": 4,
    "end_col": 5,
    "width": 4,
    "height": 3,
    "is_main_cell": true
  },
  "ghost_cell": false,
  "style": { ... }
}
```

### 关键字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `coordinate` | string | 单元格坐标，如 `"B2"` |
| `value` | any | 单元格值（数字、字符串、布尔值、公式等） |
| `type` | string | 数据类型：`string`/`number`/`boolean`/`formula`/`error` |
| `number_format` | string | 数字格式代码，如 `"0.00%"`、`"yyyy-mm-dd"` |
| `is_merged` | boolean | 是否属于合并区域 |
| `ghost_cell` | boolean | **关键**：是否为"幽灵单元格"（见下文） |

---

## 3. 合并单元格处理（核心设计）

### 3.1 概念定义

| 类型 | 说明 | 示例 |
|------|------|------|
| **主单元格 (Main Cell)** | 合并区域的左上角，存储实际数据和样式 | `B2` 是 `B2:E4` 的主单元格 |
| **幽灵单元格 (Ghost Cell)** | 合并区域内的其他单元格，视觉上不存在 | `C2`, `D2`, `B3`, `C3`... 都是幽灵 |

### 3.2 标记方式

**主单元格**：
```json
{
  "coordinate": "B2",
  "value": "季度销售数据",
  "is_merged": true,
  "ghost_cell": false,
  "merged_range": {
    "start_row": 2, "start_col": 2,
    "end_row": 4, "end_col": 5,
    "width": 4, "height": 3,
    "is_main_cell": true
  },
  "style": { ... }  // 完整样式
}
```

**幽灵单元格**：
```json
{
  "coordinate": "C2",
  "value": null,
  "is_merged": true,
  "ghost_cell": true,
  "merged_range": {
    "start_row": 2, "start_col": 2,
    "end_row": 4, "end_col": 5,
    "width": 4, "height": 3,
    "is_main_cell": false
  }
  // 注意：幽灵单元格无 style 字段，样式继承自主单元格
}
```

### 3.3 Merged Ranges 汇总

便于快速查询所有合并区域：

```json
"merged_ranges": [
  {
    "range": "B2:E4",
    "start": "B2",
    "end": "E4",
    "width": 4,
    "height": 3,
    "value": "季度销售数据"
  },
  {
    "range": "A10:A15",
    "start": "A10",
    "end": "A15",
    "width": 1,
    "height": 6,
    "value": "合并列"
  }
]
```

---

## 4. Style（样式对象）

### 4.1 完整样式结构

```json
"style": {
  "font": { ... },
  "fill": { ... },
  "border": { ... },
  "alignment": { ... },
  "protection": { ... }
}
```

### 4.2 Font（字体）

```json
{
  "name": "微软雅黑",
  "size": 11,
  "bold": true,
  "italic": false,
  "underline": "single",
  "strike": false,
  "color": "FF0000",
  "superscript": false,
  "subscript": false
}
```

**注意**：`underline` 的值可能是 `None`/`"single"`/`"double"` 等。

### 4.3 Fill（填充/背景色）

```json
{
  "type": "solid",
  "color": "FFFF00"
}
```

或渐变填充：
```json
{
  "type": "gradientFill"
}
```

### 4.4 Border（边框）

```json
{
  "left": {
    "style": "thin",
    "color": "000000"
  },
  "right": {
    "style": "medium",
    "color": "FF0000"
  },
  "top": null,
  "bottom": {
    "style": "double",
    "color": "0000FF"
  },
  "diagonal": null
}
```

边框样式值：`None`/`"thin"`/`"medium"`/`"thick"`/`"double"`/`"dashed"` 等。

### 4.5 Alignment（对齐）

```json
{
  "horizontal": "center",
  "vertical": "center",
  "wrap_text": true,
  "shrink_to_fit": false,
  "indent": 0,
  "text_rotation": 0
}
```

`horizontal` 值：`left`/`center`/`right`/`justify`/`fill`/`distributed`

### 4.6 Protection（保护）

```json
{
  "locked": true,
  "hidden": false
}
```

---

## 5. 行列维度

记录列宽和行高：

```json
"column_dimensions": {
  "A": {"width": 15.5, "auto_size": false, "hidden": false},
  "B": {"width": 25.0, "auto_size": true, "hidden": false},
  "C": {"width": 10, "hidden": true}
},
"row_dimensions": {
  "1": {"height": 30, "hidden": false},
  "5": {"height": 50, "hidden": false}
}
```

---

## 6. 其他工作表属性

### 6.1 Freeze Panes（冻结窗格）

```json
"freeze_panes": {
  "row": 3,    // 冻结前3行
  "col": 2     // 冻结前2列
}
```

### 6.2 Sheet Properties（工作表属性）

```json
"sheet_properties": {
  "tab_color": "FF00FF",
  "auto_filter": "A1:D100"
}
```

---

## 7. Matrix View（矩阵视图）

可选生成，便于快速数据访问：

```json
"matrix_view": [
  ["标题1", "标题2", null, null],      // 第1行
  ["数据1", null, null, null],           // 第2行（合并单元格只显示一次值）
  [null, null, null, null],              // 第3行（幽灵单元格位置为null）
  ["合计", 100, 200, 300]                // 第4行
]
```

**生成规则**：
- 遍历所有单元格
- 遇到主单元格：显示值
- 遇到幽灵单元格：置为 `null`（表示该位置被合并区域占据）

---

当你需要将一个xlxs文件转换为json格式时：

- read_xlsx：
用法：
run_command: 
arguments: python [base_path]/scripts/read_xlsx.py [input.xlsx] [output.json]（可选，默认为输入文件名） --sheet [转换的sheets（默认all）]

当你需要创建一个新的xlsx文件时使用以下脚本：
create_xlsx：
run_command: 
arguments: python [base_path]/scripts/create_xlsx.py [input.json] [output.xlsx]（可选，默认为输入文件名）


当你想要修改部分内容时，无需重写整个文件，可以先将文件转为json格式后使用StrReplace工具替换后转换回去。

其余功能可以编写Python脚本实现。

尽量编写少的内容。