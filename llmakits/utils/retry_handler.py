"""
重试处理组件
负责处理API请求的重试逻辑、错误处理和异常恢复
"""

from funcguard import print_line, time_wait
from typing import Dict, Tuple, Any
from ..message import rebuild_messages_single_image, convert_images_to_base64
from .retry_config import (
    IMAGE_DOWNLOAD_ERROR_KEYWORDS,
    DEFAULT_RETRY_KEYWORDS,
    MIN_LIMIT_ERROR_KEYWORDS,
    DEFAULT_RETRY_API_KEYWORDS,
)


class RetryHandler:
    """处理API请求重试逻辑的组件"""

    def __init__(self, platform: str):
        self.platform = platform
        # 获取全局图片缓存
        self.image_cache = None
        try:
            # 注意：必须在这里导入，避免循环引用
            # dispatcher.py 导入 message.convert_to_json，而 utils.retry_handler 又导入 dispatcher.ModelDispatcher
            # 如果在模块级别导入会造成循环引用错误
            from ..dispatcher import ModelDispatcher

            self.image_cache = ModelDispatcher.get_image_cache()
        except ImportError:
            pass

    def _build_error_message(self, error_data: Dict, original_exception: Exception) -> str:
        """构建错误消息字符串

        参数:
            error_data: 包含错误信息的数据字典
            original_exception: 原始异常对象，用于备用错误消息

        返回:
            格式化后的错误消息字符串
        """
        error = error_data.get("error", {})
        message = error_data.get("message", "")

        # 如果没有message，尝试从error中获取
        if not message:
            message = error.get("message", str(original_exception))

        metadata = error.get("metadata", {})  # openrouter
        raw = metadata.get("raw", "")
        provider_name = metadata.get("provider_name", "")

        # 构建基础错误消息
        error_parts = [f"message: {message}"]

        # 只在有值时添加provider信息
        if provider_name:
            error_parts.append(f"provider: {provider_name}")

        # 只在有值时添加detail信息
        if raw:
            error_parts.append(f"detail: {raw}")

        return " , ".join(error_parts)

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
                    error_message = self._build_error_message(res, e)

                # hasattr 检查 response 是否有 json 方法
                elif hasattr(response, 'json'):
                    res = response.json()
                    # 判断 res 是否是列表
                    if isinstance(res, list):
                        res = res[0]
                    error_message = self._build_error_message(res, e)

            except (AttributeError, ValueError):
                error_message = str(e)

        return error_message

    def should_retry_for_rate_limit(self, error_message: str) -> bool:
        """判断是否因为限流而重试"""
        return any(keyword in error_message for keyword in DEFAULT_RETRY_KEYWORDS)

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
                # print(f"尝试将图片转换为base64格式...")
                img_list = convert_images_to_base64(img_list, self.image_cache)
                # 更新message_config，确保转换后的base64图片在后续重试中继续使用
                # message_config["img_list"] = img_list

            messages = rebuild_messages_single_image(
                self.platform,
                message_config["system_prompt"],
                message_config["user_text"],
                reject_single_image=False,
                img_list=img_list,
            )
        else:
            if any(keyword in error_message for keyword in MIN_LIMIT_ERROR_KEYWORDS):
                time_wait(60 * (api_retry_count + 1))  # 等待一段时间后重试
            else:
                time_wait(10 * (api_retry_count + 1))  # 等待一段时间后重试

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

        # 只使用第一张图片，并更新message_config
        # if message_config["img_list"]:
        #     message_config["img_list"] = [message_config["img_list"][0]]

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

        elif any(keyword in error_message for keyword in DEFAULT_RETRY_API_KEYWORDS):
            print("模型每日请求超过限制 或 免费额度已用完")
            return True, messages, True  # 需要重试且需要切换API密钥

        else:
            # 直接重新抛出原始异常，保持异常对象的完整性
            # print(f"其他异常错误：{e}")
            raise e
