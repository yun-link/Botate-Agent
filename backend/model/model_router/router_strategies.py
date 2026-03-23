from dataclasses import dataclass
from typing import Callable, Generator, List, Tuple
import json

from ..message_schemas import (
    FunctionCallContent, 
    Message, 
    ResponseContent,
    Text,
    Image,
    Audio,
    Video
)
from ..providers import ModelInfo, ThinkingConfig
from ..model import Model, get_model_info, call


class MissingPerformanceError(Exception):
    """当模型缺少性能信息时抛出的错误"""
    pass

ROUTER_PROMPT = '''<rule>
你是一个智能模型路由器，负责根据用户问题的复杂度和多模态需求，结合可用模型的性能特点，选择最适合处理当前问题的模型。

**多模态识别**：首先检查用户问题是否包含文本以外的内容（如图像、音频、视频等）。若包含，则优先选择符合策略的模型。
**思维链**：根据任务难度选择思维链类型，例如高难度任务优先选择支持思维链的模型。

**输出要求：**
- 仅输出一个纯JSON对象，不包含任何Markdown格式或额外解释。
- JSON必须包含以下字段：
  - `idx`：所选模型的编号（整数）
  - `thinking`：布尔值或是一个JSON对象或者字符串，根据每个模型的支持情况而定。
</rule>
<task>
用户问题："{user_input}"
</task>'''

@dataclass
class ModelRouteCache:
    messages: List[Message]
    result: tuple

def _check_performance_info(models: List[ModelInfo]) -> None:
    """检查所有模型是否都有性能信息
    
    Raises:
        MissingPerformanceError: 如果有模型缺少性能信息
    """
    missing_models = []
    for model in models:
        if model.performance is None:
            missing_models.append(model.model_id)
    
    if missing_models:
        raise MissingPerformanceError(
            f"以下模型缺少性能信息，无法使用模型路由功能：{', '.join(missing_models)}。"
            f"请在配置中为这些模型添加 performance 字段（包含 reasoning, writing, coding, speed, cost 指标）。"
        )


def _generate_model_infos(models):
    # 先检查性能信息
    _check_performance_info(models)
    
    model_infos = []
    for idx, model in enumerate(models):
        info = model
        model_infos.append(
            f"""模型编号：{idx}\
            模型id：{info.model_id}\
            模型是否支持思维链：{info.thinking.support_thinking}\
            模型是否支持直接回答：{info.thinking.support_Answer}\
            模型是否支持自动选择思维链：{info.thinking.support_auto}\
            模型是否支持思维强度：{info.thinking.support_effort}\
            模型推理性能：{info.performance.reasoning}\
            模型写作性能：{info.performance.writing}\
            模型代码性能：{info.performance.coding}\
            模型速度：{info.performance.speed}\
            模型省钱分数（越大越省钱）：{100-info.performance.cost}\
            模型支持模态：{'、'.join([m.__name__ for m in info.get_modality_classes()])}\
            如果选择开启或关闭模型思维在thinking部分输出true或false（直接回答）\
            ==========="""
        )
        if info.thinking.support_effort:
            model_infos[idx] += f'''\n如果模型支持思维强度并且要使用思维强度可以在thinking部分输出{'、'.join(info.thinking.effort.keys())}（思维强度不一定越高越好，越高代表耗时越长，可能是无意义的思考，建议根据问题实际难度考虑）'''
        if info.thinking.support_auto:
            model_infos[idx] += "\n如果模型支持auto模式并且要使用auto模式在thinking部分输出'auto'"
        if info.other:
            model_infos[idx] += '\n其它：'+info.other
    return ''.join(model_infos)


def _base_router_func(messages: List[Message], models: List[ModelInfo], strategy: str, cache: ModelRouteCache):
    prompt = None
    for message in messages:
        if message.role == 'user':
            prompt = message
    if cache:
        for cache_message in cache.messages:
            if cache_message == prompt:
                return cache.result
            
    router_messages = []
    user_input = f"""用户提示词：'{prompt.content}', **决策策略**：{strategy} **模型信息：**{_generate_model_infos(models)}（性能维度0-100）"""
    user_content = ROUTER_PROMPT.format(user_input=user_input)
    router_messages.append(Message('user', user_content))
    result = json.loads(
        call(
            'doubao-seed-1.8',
            messages=router_messages,
            thinking=False,
            temperature=0.1
        ).content.text
    )
    idx = result['idx']
    thinking = result['thinking']
    return idx, thinking 

def effectiveness_first(messages: List[Message], models: List[ModelInfo], cache):
    return _base_router_func(
            messages=messages,
            models=models,
            strategy='根据用户的需求，选择出对应性能指标最好的模型。',
            cache=cache
        )

def cost_first(messages: List[Message], models: List[ModelInfo], cache):
    return _base_router_func(
            messages=messages,
            models=models,
            strategy='''根据用户的需求，选择出对应性能指标合格的模型，并且倾向选择省钱分较高的模型而排除省钱分低的模型。示例："帮我修改系统变量，再在Python脚本中验证修改内容……"->推理分70以上的省钱分最低模型''',
            cache=cache
        )   

def balance(messages: List[Message], models: List[ModelInfo], cache):
    return _base_router_func(
            messages=messages,
            models=models,
            strategy='根据用户的需求，选择模型中对应性能指标合格，并且在其中选择省钱分和对应性能指标性价比最平衡的模型。',
            cache=cache
        )
