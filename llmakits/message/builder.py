"""
消息构建器
负责根据不同提供商的要求构建消息格式
"""

from typing import List, Optional, Dict, Any, Tuple
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
    user_message = {"role": "user", "content": user_content}

    if system_content:
        system_message = {"role": "system", "content": system_content}
        return [system_message, user_message]
    else:
        return [user_message]


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
    provider_name: str,
    system_prompt: str,
    user_text: str,
    include_img: bool,
    img_list: List[str],
    image_cache=None,  # 图片缓存参数
) -> tuple:
    """根据提供商构建内容格式"""

    if not include_img:
        return system_prompt, user_text

    if provider_name == "dashscope":
        user_content = [{"image": img} for img in img_list]
        user_content.append({"text": user_text})
        if system_prompt:
            system_content = [{"text": system_prompt}]
        else:
            system_content = []

    elif provider_name == "ollama":
        if system_prompt:
            system_content = system_prompt
        else:
            system_content = []
        user_content = user_text
        try:
            # todu 这里后续需要修改
            img_list = batch_download_encode_base64(img_list)
        except Exception as e:
            print(f"Ollama图片批量转换base64失败: {e}")
            raise Exception(f"图片下载或转换base64失败，url：{img_list}")

    # 兼容通用的 "openai", "modelscope", "openrouter" 格式 , 不支持 zhipu ( 可切换为 zhipu_openai 进行兼容 )
    else:
        if provider_name in ["openrouter", "gemini", "vercel", "github"]:
            # openrouter 需要base64格式的图片
            try:
                img_list = convert_images_to_base64(img_list, image_cache)  # 传递缓存
            except Exception as e:
                print(f"图片列表转base64失败: {e}")
                raise Exception(f"图片列表转base64失败，img_list：{img_list}")

        user_content = [{"type": "image_url", "image_url": {"url": img}} for img in img_list]
        if provider_name in ["gitcode"]:
            if system_prompt:
                system_prompt_user = f"# 任务角色与设定 \n{system_prompt}\n"
            else:
                system_prompt_user = ""
            user_prompt = f"# 任务相关信息 \n{user_text}\n"
            user_content.append({"type": "text", "text": system_prompt_user + user_prompt})
            system_content = []
        else:
            user_content.append({"type": "text", "text": user_text})
            if system_prompt:
                system_content = [{"type": "text", "text": system_prompt}]
            else:
                system_content = []

    return system_content, user_content


def convert_images_to_base64(img_list: List[str], image_cache=None) -> List[str]:
    """
    将图片URL列表转换为base64格式

    Args:
        img_list: 图片URL列表

    Returns:
        转换后的图片URL列表（仅保留转换成功的base64格式）
        注意：转换后的图片列表，不支持 sdk/platform/provider = zhipu ,
            如需使用，请使用名称 zhipu_openai 兼容 openai的格式
    """
    if not img_list:
        raise ValueError("图片 img_list 不能为空!")

    # 如果没有传入缓存对象，尝试从dispatcher获取全局缓存
    if image_cache is None:
        try:
            # 注意：必须在这里导入，避免循环引用
            # dispatcher.py 导入 message.convert_to_json，而 message.builder 又导入 dispatcher.ModelDispatcher
            # 如果在模块级别导入会造成循环引用错误
            from ..dispatcher import ModelDispatcher

            image_cache = ModelDispatcher.get_image_cache()
        except ImportError:
            # 如果无法导入，不使用缓存
            image_cache = None

    processed_img_list = []
    valid_extensions = ('.jpg', '.jpeg', '.png')
    successful_conversions = 0  # 成功转换的图片数量
    total_valid_images = 0  # 需要转换的有效图片数量

    for img_url in img_list:
        # 检查是否已经是base64格式
        if img_url.startswith('data:image/') and ';base64,' in img_url:
            # 已经是base64格式，直接添加到结果列表
            processed_img_list.append(img_url)
            # print(f"图片已经是base64格式，无需转换: {img_url}...")
            continue

        # 检查是否为有效的图片URL
        img_lower = img_url.lower()
        if img_lower.endswith(valid_extensions):
            total_valid_images += 1

            # 尝试从缓存中获取
            cached_base64 = None
            if image_cache is not None:
                cached_base64 = image_cache.get(img_url)
                if cached_base64:
                    print(f"已从缓存中获取图片base64: {img_url}")
                    # 构建完整的base64 URL
                    mime_type = 'image/jpeg' if img_lower.endswith(('.jpg', '.jpeg')) else 'image/png'
                    base64_url = f"data:{mime_type};base64,{cached_base64}"
                    processed_img_list.append(base64_url)
                    successful_conversions += 1
                    continue

            try:
                # 下载并转换为base64
                base64_str = download_encode_base64(img_url)
                if base64_str:
                    # 存入缓存
                    if image_cache is not None:
                        image_cache.put(img_url, base64_str)
                        # print(f"已将图片base64存入缓存: {img_url}")
                    # 构建base64格式的图片URL
                    mime_type = 'image/jpeg' if img_lower.endswith(('.jpg', '.jpeg')) else 'image/png'
                    base64_url = f"data:{mime_type};base64,{base64_str}"
                    processed_img_list.append(base64_url)
                    successful_conversions += 1
                    print(f"已将图片转换为base64格式: {img_url}")
                else:
                    print(f"转换后,base64_str无效，已跳过：{img_url} ")
                    continue

            except Exception as e:
                print(f"图片转base64失败: {img_url}\n{e}")
                continue
        else:
            processed_img_list.append(img_url)

    # 只有当所有有效图片都转换失败时，才抛出异常
    if total_valid_images > 0 and successful_conversions == 0:
        raise Exception(f"图片下载或转换base64失败，url：{img_list}")

    return processed_img_list


def prepare_request_data(platform: str, messages: Any, message_info: Optional[Dict]) -> Tuple[Any, Dict]:
    """准备请求数据

    Args:
        platform: 平台名称
        messages: 请求消息对象
        message_info: 消息信息字典，包含系统提示词、用户文本、是否包含图片和图片列表等

    Returns:
        Tuple[Any, Dict]: (更新后的消息对象, 消息配置字典)
    """
    message_config = {"user_text": "", "include_img": False, "img_list": []}

    if message_info is not None:
        message_config.update(
            {
                "user_text": message_info["user_text"],
                "include_img": message_info.get("include_img", False),
                "img_list": message_info.get("img_list", []),
            }
        )

        system_prompt = message_info["system_prompt"]
        if system_prompt:
            message_config["system_prompt"] = system_prompt

        messages = prepare_messages(
            platform,
            message_config.get("system_prompt", ""),
            message_config["user_text"],
            message_config["include_img"],
            message_config["img_list"],
        )
    return messages, message_config
