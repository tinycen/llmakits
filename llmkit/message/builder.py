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
    img_list: Optional[List[str]] = None
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
        if include_img :
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
    include_img: bool = False,
    img_list: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    重新构造messages，只使用第一张图片
    
    Args:
        provider_name: 提供商名称
        system_prompt: 系统提示词
        user_text: 用户文本
        include_img: 是否包含图片
        img_list: 图片URL列表
    
    Returns:
        格式化后的消息列表（只包含第一张图片）
    """
    if img_list is None:
        img_list = []
    
    if len(img_list) == 1 and include_img :
        print("异常：图片数量 未超出限制")
        print(f"img_list : {img_list}")
        raise Exception("异常：图片数量 == 1，未超出限制")

    # 重新构造messages，只使用第一张图片
    return prepare_messages(
        provider_name, 
        system_prompt, 
        user_text, 
        include_img,
        [img_list[0]] if img_list else []
    )


def _build_content_by_provider(
    provider_name: str,
    system_prompt: str,
    user_text: str,
    include_img: bool,
    img_list: List[str]
) -> tuple:
    """根据提供商构建内容格式"""
    
    if not include_img:
        return system_prompt, user_text
    
    if provider_name == "dashscope":
        user_content = [{"image": img} for img in img_list]
        user_content.append({"text": user_text})
        system_content = [{"text": system_prompt}]
        
    elif provider_name in ["zhipu", "openai", "modelscope"]:
        user_content = [{"type": "image_url", "image_url": {"url": img}} for img in img_list]
        user_content.append({"type": "text", "text": user_text})
        system_content = [{"type": "text", "text": system_prompt}]
        
    elif provider_name == "ollama":
        system_content = system_prompt
        user_content = user_text
        img_list = batch_download_encode_base64(img_list)
        
    else:
        raise ValueError("Unsupported provider_name. Use 'dashscope', 'zhipu', 'openai', 'modelscope', or 'ollama'.")
    
    return system_content, user_content


def _build_message_structure(
    provider_name: str,
    system_content: Any,
    user_content: Any,
    img_list: List[str]
) -> List[Dict[str, Any]]:
    """构建消息结构"""
    
    system_message = {"role": "system", "content": system_content}
    user_message = {"role": "user", "content": user_content}
    
    # 为ollama添加图片base64编码
    if provider_name == "ollama" and len(img_list) > 0:
        user_message["images"] = img_list
    
    return [system_message, user_message]