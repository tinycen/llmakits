"""
消息构建器
负责根据不同提供商的要求构建消息格式
"""

from typing import List, Optional, Dict, Any
from filekits.base_io.down_load import batch_download_encode_base64


def prepare_messages(
    provider_name: str,
    system_prompt: str,
    user_text: str,
    include_img: bool = False,
    img_list: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    根据提供商名称准备消息格式

    Args:
        provider_name: 提供商名称 ('dashscope', 'zhipu', 'openai', 'modelscope', 'ollama')
        system_prompt: 系统提示词
        user_text: 用户文本
        include_img: 是否包含图片
        img_list: 图片URL列表

    Returns:
        格式化后的消息列表
    """
    if img_list is None:
        if include_img:
            raise ValueError("包含图片的消息，图片 img_list 不能为空。")
        img_list = []

    if include_img and len(img_list) < 1:
        raise ValueError("包含图片的消息，图片 img_list 不能为空。")

    # 根据提供商构建不同格式的消息
    system_content, user_content = _build_content_by_provider(
        provider_name, system_prompt, user_text, include_img, img_list
    )

    # 构建消息结构
    messages = _build_message_structure(provider_name, system_content, user_content, img_list)

    return messages


def rebuild_messages_single_image(
    provider_name: str,
    system_prompt: str,
    user_text: str,
    reject_single_image: bool,
    img_list: list,
) -> List[Dict[str, Any]]:
    """
    重新构造messages，只使用第一张图片

    Args:
        provider_name: 提供商名称
        system_prompt: 系统提示词
        user_text: 用户文本
        reject_single_image: 是否禁止单张图片（为True时若图片数量为1则抛异常）
        img_list: 图片URL列表

    Returns:
        格式化后的消息列表（只包含第一张图片）
    """
    if not img_list:
        raise ValueError("图片 img_list 不能为空!")

    img_num = len(img_list)

    if reject_single_image:
        if img_num == 1:
            error_message = "异常：图片数量 == 1，未超出限制"
            print(f"{error_message}，img_list : {img_list}")
            raise Exception(error_message)

    # 重新构造messages，只使用第一张图片
    return prepare_messages(provider_name, system_prompt, user_text, True, [img_list[0]] if img_list else [])


def _build_content_by_provider(
    provider_name: str, system_prompt: str, user_text: str, include_img: bool, img_list: List[str]
) -> tuple:
    """根据提供商构建内容格式"""

    if not include_img:
        return system_prompt, user_text

    if provider_name == "dashscope":
        user_content = [{"image": img} for img in img_list]
        user_content.append({"text": user_text})
        system_content = [{"text": system_prompt}]

    elif provider_name == "ollama":
        system_content = system_prompt
        user_content = user_text
        img_list = batch_download_encode_base64(img_list)

    else:
        # 兼容通用的 "openai", "zhipu", "modelscope" 格式
        user_content = [{"type": "image_url", "image_url": {"url": img}} for img in img_list]
        user_content.append({"type": "text", "text": user_text})
        system_content = [{"type": "text", "text": system_prompt}]

    return system_content, user_content


def _build_message_structure(
    provider_name: str, system_content: Any, user_content: Any, img_list: List[str]
) -> List[Dict[str, Any]]:
    """构建消息结构"""

    system_message = {"role": "system", "content": system_content}
    user_message = {"role": "user", "content": user_content}

    # 为ollama添加图片base64编码
    if provider_name == "ollama" and len(img_list) > 0:
        user_message["images"] = img_list

    return [system_message, user_message]
