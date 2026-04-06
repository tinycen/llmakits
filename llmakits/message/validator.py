"""
消息验证器
负责验证消息格式和内容的有效性
"""

from typing import Any, Dict, List

# 定义不同文件类型的base64特征
BASE64_SIGNATURES = {
    "jpeg": ("/9j/", "JPEG图片"),
    "png": ("iVBORw0KGgo", "PNG图片"),
    "gif": ("R0lGODlh", "GIF图片"),
    "html": ("PCFET0NUWVBFIGh0bWw+", "HTML文档"),
}


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


def validate_base64_content(base64_str: str, expected_type: str = "image") -> tuple[bool, str]:
    """
    验证base64字符串的内容类型

    Args:
        base64_str: base64编码的字符串
        expected_type: 期望的内容类型，默认为"image"，可以是"image"或"any"

    Returns:
        (是否有效, 错误信息)
    """
    if not base64_str:
        return False, "base64字符串为空"

    # 当指定为图片类型时，检查是否为HTML（应该报错）
    if expected_type == "image" and base64_str.startswith(BASE64_SIGNATURES["html"][0]):
        return False, f"检测到 base64 内容为：HTML，请检查URL是否为有效的图片链接(或者文件下载失败)"

    # 如果不限制类型，直接通过
    if expected_type == "any":
        return True, ""

    # 验证是否为图片类型
    if expected_type == "image":
        image_signatures = [BASE64_SIGNATURES["jpeg"][0], BASE64_SIGNATURES["png"][0], BASE64_SIGNATURES["gif"][0]]
        for sig in image_signatures:
            if base64_str.startswith(sig):
                return True, ""
        return False, "base64内容不是有效的图片格式(JPEG/PNG/GIF)"

    return True, ""
