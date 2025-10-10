"""
重试处理组件
负责处理API请求的重试逻辑、错误处理和异常恢复
"""

import time
from funcguard.printer import print_line
from funcguard.core import timeout_handler
from typing import Dict, Tuple, Any, Optional
from ..message import prepare_messages, rebuild_messages_single_image, convert_images_to_base64


# 图片下载相关的错误关键词列表
IMAGE_DOWNLOAD_ERROR_KEYWORDS = [
    "Download the media resource timed out",
    "Failed to download multimodal content",
    "Download multimodal file timed out",
]

# 默认的重试关键词列表
DEFAULT_RETRY_KEYWORDS = [
    "Too many requests",
    "Allocated quota exceeded, please increase your quota limit",
    "Max retries exceeded with url",
    "Requests rate limit exceeded, please try again later",
    "Free credits temporarily have rate limits",  # vercel
]

DEFAULT_RETRY_KEYWORDS.extend(IMAGE_DOWNLOAD_ERROR_KEYWORDS)


class RetryHandler:
    """处理API请求重试逻辑的组件"""

    def __init__(self, platform: str):
        self.platform = platform
        self.retry_keywords = DEFAULT_RETRY_KEYWORDS

    def prepare_request_data(self, messages: Any, message_info: Optional[Dict]) -> Tuple[Any, Dict]:
        """准备请求数据"""
        message_config = {"system_prompt": "", "user_text": "", "include_img": False, "img_list": []}

        if message_info is not None:
            message_config.update(
                {
                    "system_prompt": message_info["system_prompt"],
                    "user_text": message_info["user_text"],
                    "include_img": message_info.get("include_img", False),
                    "img_list": message_info.get("img_list", []),
                }
            )

            messages = prepare_messages(
                self.platform,
                message_config["system_prompt"],
                message_config["user_text"],
                message_config["include_img"],
                message_config["img_list"],
            )

        return messages, message_config

    def extract_error_message(self, e: Exception) -> str:
        """提取错误信息"""
        error_message = str(e)
        response = getattr(e, 'response', None)

        # 如果异常对象本身就是response（来自handle_response的直接抛出）
        if hasattr(e, 'model_dump'):
            response = e

        if response:
            try:
                if hasattr(response, 'model_dump'):  # 兼容 openai
                    res = response.model_dump()
                    error = res.get("error", {})
                    message = error.get("message", "")
                    metadata = error.get("metadata", {})
                    raw = metadata.get("raw", "")
                    provider_name = metadata.get("provider_name", "")
                    error_message = f"message: {message} : provider: {provider_name} , {raw}"

                # hasattr 检查 response 是否有 json 方法
                elif hasattr(response, 'json'):
                    res = response.json()
                    error = res.get("error", res.get("errors", {}))
                    error_message = error.get("message", str(e))

            except (AttributeError, ValueError):
                error_message = str(e)

        return error_message

    def should_retry_for_rate_limit(self, error_message: str) -> bool:
        """判断是否因为限流而重试"""
        return any(keyword in error_message for keyword in self.retry_keywords)

    def should_retry_for_image_error(self, error_message: str, message_config: Dict) -> bool:
        """判断是否因为图片错误而重试"""
        image_errors = ["输入图片数量超过限制", "图片输入格式/解析错误"]
        return any(error in error_message for error in image_errors) and message_config["include_img"]

    def handle_rate_limit_error(
        self, error_message: str, api_retry_count: int, messages: Any, message_config: Dict
    ) -> Tuple[bool, Any]:
        """处理限流错误

        参数:
            error_message: 错误信息字符串
            api_retry_count: 当前API重试次数（从0开始计数）
            messages: 请求消息对象
            message_config: 消息配置数据字典

        返回:
            Tuple[bool, Any]: (是否继续重试, 更新后的messages对象)
        """
        print(f"请求被限流 或者 网络连接失败，正在第 {api_retry_count + 1} 次重试……")
        # 如果图片：下载或读取 出现问题
        if any(keyword in error_message for keyword in IMAGE_DOWNLOAD_ERROR_KEYWORDS) and message_config["include_img"]:

            img_list = message_config["img_list"]
            print(f"img_list: {img_list}")

            # 第3次尝试时，检测图片格式并进行base64转换
            if api_retry_count == 1 and img_list:
                print(f"尝试将图片转换为base64格式...")
                img_list = convert_images_to_base64(img_list)

            messages = rebuild_messages_single_image(
                self.platform,
                message_config["system_prompt"],
                message_config["user_text"],
                reject_single_image=False,
                img_list=img_list,
            )
        else:
            time.sleep(10 * (api_retry_count + 1))  # 等待一段时间后重试

        return True, messages

    def handle_image_error(self, messages: Any, message_config: Dict) -> Tuple[bool, Any]:
        """处理图片相关错误

        参数:
            messages: 请求消息对象
            message_config: 消息配置数据字典

        返回:
            Tuple[bool, Any]: (是否继续重试, 更新后的messages对象)
        """

        print("输入图片数量超过限制 或 图片输入格式/解析错误，正在（ 限制图片数量 = 1 ）然后重试...")

        messages = rebuild_messages_single_image(
            self.platform,
            message_config["system_prompt"],
            message_config["user_text"],
            reject_single_image=True,
            img_list=message_config["img_list"],
        )

        return True, messages

    def handle_exception(
        self, e: Exception, api_retry_count: int, messages: Any, message_config: Dict, platform: str, model_name: str
    ) -> Tuple[bool, Any, bool]:
        """处理异常和重试逻辑

        参数:
            e: 异常对象
            api_retry_count: 当前API重试次数（从0开始计数）
            messages: 请求消息对象
            message_config: 消息配置数据字典
            platform: 云服务商平台名称
            model_name: 模型名称

        返回:
            Tuple[bool, Any, bool]: (是否继续重试, 更新后的messages对象, 是否需要切换API密钥)
        """
        # 打印当前的模型信息
        print_line()
        print(f"当前 云服务商: {platform}，模型: {model_name}")
        # print(e)

        # 获取错误信息
        error_message = self.extract_error_message(e)

        # 判断是否应该重试
        if self.should_retry_for_rate_limit(error_message):
            should_retry, updated_messages = self.handle_rate_limit_error(
                error_message, api_retry_count, messages, message_config
            )
            return should_retry, updated_messages, False

        elif self.should_retry_for_image_error(error_message, message_config):
            should_retry, updated_messages = self.handle_image_error(messages, message_config)
            return should_retry, updated_messages, False

        elif "Request limit exceeded" in error_message:  # 适用于 modelscope
            print("模型每日请求超过限制")
            return True, messages, True  # 需要重试且需要切换API密钥

        elif "The free tier of the model has been exhausted" in error_message:  # 适用于 dashscope
            print("免费额度已用完")
            return True, messages, True  # 需要重试且需要切换API密钥

        else:
            # 直接重新抛出原始异常，保持异常对象的完整性
            # print(f"其他异常错误：{e}")
            raise e


class ResponseHandler:
    """处理API响应的组件"""

    @staticmethod
    def handle_response(
        response: Any, stream: bool, stream_real: bool, process_stream_response_func: Any
    ) -> Tuple[Any, int]:
        """处理响应"""

        total_tokens = 0

        if stream:
            if stream_real:
                result = response
            else:
                result = timeout_handler(process_stream_response_func, args=(response,), execution_timeout=180)
        else:
            if response.choices:
                result = response.choices[0].message.content
                total_tokens = response.usage.total_tokens
            else:
                # 如果没有choices，直接抛出原始response对象
                print(f"响应中没有choices，原始响应：{response}")
                raise response

        return result, total_tokens
