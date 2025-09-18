"""
消息验证器
负责验证消息格式和内容的有效性
"""

from typing import Any, Dict, List


def validate_message_format(messages: List[Dict[str, Any]], provider_name: str) -> bool:
    """
    验证消息格式是否符合指定提供商的要求

    Args:
        messages: 消息列表
        provider_name: 提供商名称

    Returns:
        True如果格式有效，False否则
    """

    if len(messages) < 1:
        return False

    # 验证每条消息的基本结构
    for message in messages:
        if not isinstance(message, dict):
            return False

        if 'role' not in message or 'content' not in message:
            return False

        if message['role'] not in ['system', 'user', 'assistant']:
            return False

    # 根据提供商验证特定格式
    return _validate_provider_format(messages, provider_name)


def _validate_provider_format(messages: List[Dict[str, Any]], provider_name: str) -> bool:
    """验证特定提供商的消息格式"""

    if provider_name == "dashscope":
        return _validate_dashscope_format(messages)
    elif provider_name in ["zhipu", "openai", "modelscope"]:
        return _validate_openai_format(messages)
    elif provider_name == "ollama":
        return _validate_ollama_format(messages)
    else:
        return False


def _validate_dashscope_format(messages: List[Dict[str, Any]]) -> bool:
    """验证DashScope格式"""
    try:
        for message in messages:
            content = message['content']
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        return False
                    if 'text' not in item and 'image' not in item:
                        return False
            elif not isinstance(content, str):
                return False
        return True
    except Exception:
        return False


def _validate_openai_format(messages: List[Dict[str, Any]]) -> bool:
    """验证OpenAI格式"""
    try:
        for message in messages:
            content = message['content']
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        return False
                    if item.get('type') == 'image_url':
                        if 'image_url' not in item or not isinstance(item['image_url'], dict):
                            return False
                    elif item.get('type') == 'text':
                        if 'text' not in item:
                            return False
            elif not isinstance(content, str):
                return False
        return True
    except Exception:
        return False


def _validate_ollama_format(messages: List[Dict[str, Any]]) -> bool:
    """验证Ollama格式"""
    try:
        for message in messages:
            content = message['content']
            if not isinstance(content, str):
                return False
        return True
    except Exception:
        return False
