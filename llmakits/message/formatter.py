"""
消息格式化器
负责处理消息内容的格式化和解析
"""

import re
import json
from typing import Any, Union, Tuple


def remove_think_section(text: str) -> str:
    """
    移除思考段落（<think>...</think>标签内的内容）

    Args:
        text: 原始文本

    Returns:
        移除思考段落后的文本
    """
    start_tag = '<think>'
    if start_tag not in text:
        return text.strip()

    end_tag = '</think>'
    start_index = text.find(start_tag)
    end_index = text.find(end_tag)

    if start_index != -1 and end_index != -1:
        end_index += len(end_tag)
        new_text = text[:start_index] + text[end_index:]
        return new_text.strip()
    else:
        return text.strip()


def extract_json_from_string(text_with_json: str) -> str:
    """
    从包含JSON内容的字符串中提取JSON字符串，优先匹配```json ... ```代码块

    Args:
        text_with_json: 包含JSON内容的字符串

    Returns:
        提取到的JSON字符串

    Raises:
        ValueError: 如果未找到有效的JSON代码块
    """
    # 优先查找```json ... ```代码块，优先尝试对象 {}，其次数组 []
    patterns = [
        r"```json\s*(\{[\s\S]*?\})\s*```",  # 优先匹配对象 {}
        r"```json\s*(\[[\s\S]*?\])\s*```",  # 其次匹配数组 []
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_with_json)
        for match in matches:
            json_string = match.strip()
            try:
                json.loads(json_string)
                return json_string
            except json.JSONDecodeError:
                print(f"提取的json代码块无效: {json_string}")
                continue

    # print(text_with_json)
    raise ValueError("未找到有效的JSON代码块")


def convert_to_json(text: str) -> Any:
    """
    将响应结果转换为JSON格式

    Args:
        text: 原始文本

    Returns:
        解析后的JSON对象

    Raises:
        Exception: 如果无法解析为JSON格式
    """
    processed_text = remove_think_section(text)
    if processed_text:
        converted_json = None

        try:
            if processed_text.startswith("```json"):
                processed_text = processed_text.strip("```json\n")

            # 首先尝试直接解析JSON
            converted_json = json.loads(processed_text)
        except json.JSONDecodeError:
            try:
                # 尝试使用eval作为备选方案（谨慎使用）
                converted_json = eval(processed_text)
            except:
                # 如果eval也失败，尝试提取JSON字符串
                try:
                    extracted_json = extract_json_from_string(processed_text)
                    if extracted_json:
                        converted_json = json.loads(extracted_json)
                except:
                    pass

        if converted_json is not None:
            if "answer" in converted_json:  # zhipu 'glm-4-flash-250414' 模型会返回 answer 字段
                answer = converted_json["answer"]
                if isinstance(answer, (dict, list)):
                    return answer
                elif isinstance(answer, str):
                    # 只对字符串类型的answer尝试递归解析
                    return convert_to_json(answer)
                else:
                    return answer
            else:
                return converted_json

    print("无法解析为json格式:")
    print("原始文本:", text)
    print("处理后文本:", processed_text)
    raise Exception("format_json_error,无法解析为json格式")


def extract_field(message: Union[str, dict], *target_fields: str) -> Union[Any, Tuple[Any, ...]]:
    """
    将响应结果转为json，并获取其中的指定字段

    Args:
        message: 消息内容（字符串或字典）
        *target_fields: 要提取的字段名

    Returns:
        单个字段值或多个字段的元组

    Raises:
        KeyError: 如果指定字段不存在
    """
    if isinstance(message, dict):
        result = message
    else:
        result = convert_to_json(message)

    try:
        if len(target_fields) == 1:
            return result[target_fields[0]]  # 只有一个字段时，直接返回该字段的值
        return tuple(result[field] for field in target_fields)  # 多个字段时，返回元组
    except KeyError as e:
        print(message)
        raise KeyError(f"字段 {e} 不存在于消息中") from e
