"""
模型调度器
负责多模型故障转移和负载均衡
"""

from typing import List, Dict, Any, Optional, Callable
from llmkit.message import convert_to_json


def send_with_fallback(
    message_info: Dict[str, Any],
    llm_models: List[Dict[str, Any]],
    format_json: bool = False,
    validate_func: Optional[Callable[[str], bool]] = None
) -> tuple[str, int, int]:
    """
    多模型调度器 - 支持故障转移和重试
    
    Args:
        message_info: 消息配置信息
        llm_models: LLM模型列表，每个元素包含model、sdk_name等
        format_json: 是否格式化为JSON
        validate_func: 结果验证函数
        
    Returns:
        (返回消息, token总数, 重试次数)
    """
    retry_count = 0
    models_num = len(llm_models)

    for idx, model_info in enumerate(llm_models):
        base_model_info = f"{idx+1}/{models_num} Model {model_info['sdk_name']} : {model_info.get('model_name', 'unknown_model')}"
        try:
            return_message, total_tokens = model_info["model"].send_message([], message_info)
            if format_json:
                return_message = convert_to_json(return_message)
            
            # 如果有校验函数，校验不通过则继续下一个模型
            if validate_func is not None and not validate_func(return_message):
                print(base_model_info)
                print("输出结果：条件校验失败, trying next model ...")
                retry_count += 1
                continue
                
            return return_message, total_tokens, retry_count
            
        except Exception as e:
            print(base_model_info)
            if idx < models_num - 1:
                print("model failed, trying next model ...")
                retry_count += 1
                continue
            else:
                raise e

    # 如果所有模型都失败
    raise Exception("All models failed to send message.")