"""
消息构建器
负责根据不同提供商的要求构建消息格式
"""

from typing import List, Optional, Dict, Any
from filekits.base_io import download_encode_base64, batch_download_encode_base64


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
        try:
            img_list = batch_download_encode_base64(img_list)
        except Exception as e:
            print(f"Ollama图片批量转换base64失败: {e}")
            raise Exception(f"图片下载或转换base64失败，url：{img_list}")

    # 兼容通用的 "openai", "zhipu", "modelscope" 格式
    else:
        if provider_name in ["openrouter", "gemini"]:
            # openrouter 需要base64格式的图片
            try:
                img_list = convert_images_to_base64(img_list)
            except Exception as e:
                print(f"OpenRouter图片转换base64失败: {e}")
                raise Exception(f"图片下载或转换base64失败，url：{img_list}")

        user_content = [{"type": "image_url", "image_url": {"url": img}} for img in img_list]
        user_content.append({"type": "text", "text": user_text})
        system_content = [{"type": "text", "text": system_prompt}]

    return system_content, user_content


def convert_images_to_base64(img_list: List[str]) -> List[str]:
    """
    将图片URL列表转换为base64格式

    Args:
        img_list: 图片URL列表

    Returns:
        转换后的图片URL列表（base64格式的保留，非图片格式的保持原样）
    """
    if not img_list:
        raise ValueError("图片 img_list 不能为空!")

    processed_img_list = []
    valid_extensions = ('.jpg', '.jpeg', '.png')
    successful_conversions = 0  # 成功转换的图片数量
    total_valid_images = 0  # 需要转换的有效图片数量

    for img_url in img_list:
        # 检查是否已经是base64格式
        if img_url.startswith('data:image/') and ';base64,' in img_url:
            # 已经是base64格式，直接添加到结果列表
            processed_img_list.append(img_url)
            print(f"图片已经是base64格式，无需转换: {img_url[:50]}...")
            continue

        # 检查是否为有效的图片URL
        img_lower = img_url.lower()
        if img_lower.endswith(valid_extensions):
            total_valid_images += 1
            try:
                # 下载并转换为base64
                base64_str = download_encode_base64(img_url)
                if base64_str:
                    # 构建base64格式的图片URL
                    mime_type = 'image/jpeg' if img_lower.endswith(('.jpg', '.jpeg')) else 'image/png'
                    base64_url = f"data:{mime_type};base64,{base64_str}"
                    processed_img_list.append(base64_url)
                    successful_conversions += 1
                    print(f"已将图片转换为base64格式: {img_url}")
                else:
                    print(f"图片 {img_url} 转换为base64失败，保持原始URL")
                    processed_img_list.append(img_url)
            except Exception as e:
                print(f"转换图片为base64失败 {img_url}: {e}")
                processed_img_list.append(img_url)
        else:
            processed_img_list.append(img_url)

    # 只有当所有有效图片都转换失败时，才抛出异常
    if total_valid_images > 0 and successful_conversions == 0:
        raise Exception(f"图片下载或转换base64失败，url：{img_list}")

    return processed_img_list


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
