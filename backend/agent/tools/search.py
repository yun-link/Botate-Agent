"""
搜索工具模块

提供网络搜索功能。
"""

import os
import json
import requests
from model.tool import Tool


def _web_search_handler(params: dict) -> str:
    """
    网络搜索处理函数
    
    Args:
        params: 包含以下键的字典：
            - query: 搜索关键词
            - type: 搜索类型（text/image/video），默认为text
            
    Returns:
        搜索结果信息
    """
    query = params.get("query")
    search_type = params.get("type", "text")
    
    if not query:
        return "错误：未提供搜索关键词"
    
    # 从环境变量获取百度API密钥
    api_key = os.environ.get("BAIDU_API_KEY")
    if not api_key:
        return "错误：未设置环境变量 BAIDU_API_KEY"
    
    try:
        url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"
        
        payload = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [
                {
                    "type": "web",
                    "top_k": 50 if search_type == "text" else 0
                },
                {
                    "type": "image",
                    "top_k": 30 if search_type == "image" else 0
                },
                {
                    "type": "video",
                    "top_k": 10 if search_type == "video" else 0
                }
            ],
            "search_recency_filter": "mouth"
        }, ensure_ascii=False)
        
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
        response_data = json.loads(response.text)
        
        if 'references' not in response_data:
            return f"错误：搜索结果格式异常 - {response.text}"
        
        references = response_data['references'][:10]
        result_string = ""
        for web_page in references:
            result_string += f"[webpage {web_page['id']} begin]\n"
            result_string += f"[webpage title]  {web_page['title']}\n"
            result_string += f"[webpage url] {web_page['url']}\n"
            result_string += f"[webpage content begin]\n{web_page['content']}\n[webpage content end]\n"
            result_string += f"[webpage {web_page['id']} end]\n\n"
        
        return result_string if result_string else "未找到相关搜索结果"
    except requests.RequestException as e:
        return f"错误：网络请求失败 - {str(e)}"
    except json.JSONDecodeError as e:
        return f"错误：解析响应失败 - {str(e)}"
    except Exception as e:
        return f"错误：搜索时发生异常 - {str(e)}"


# 定义 WebSearch 工具
WebSearch = Tool(
    name="WebSearch",
    description="联网搜索工具。使用百度搜索API进行网络搜索，支持文本、图片和视频搜索。返回搜索结果的网页标题、URL和内容摘要。",
    handler=_web_search_handler,
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词或查询内容"
            },
            "type": {
                "type": "string",
                "description": "搜索类型：text（文本搜索）、image（图片搜索）、video（视频搜索），默认为text",
                "enum": ["text", "image", "video"]
            }
        },
        "required": ["query"]
    }
)
