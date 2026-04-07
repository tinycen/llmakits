"""
重试处理组件
负责处理API请求的重试逻辑、错误处理和异常恢复
"""

from funcguard import print_block, print_line, time_wait
from typing import Dict, Tuple, Any, List, Set
from urllib.parse import urlparse
from ..message import rebuild_messages_single_image, convert_images_to_base64
from .retry_state import get_retry_state
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
        self._retry_state = get_retry_state()
        self.force_base64_domains: Set[str] = self._retry_state["force_base64_domains"]
        self.domain_failure_stats: Dict[str, Dict[str, int]] = self._retry_state["domain_failure_stats"]
        self._last_failed_domain = self._retry_state["last_failed_domain"]
        # 获取全局图片缓存
        self.image_cache = None
        try:
            # 注意：必须在这里导入，避免循环引用
            # dispatcher.py 导入 message.convert_to_json，而 utils.retry_handler 又导入 dispatcher.ModelDispatcher
            # 如果在模块级别导入会造成循环引用错误
            from ..dispatcher import ModelDispatcher

            self.image_cache = ModelDispatcher.get_image_cache()
            # 重试状态直接来自 utils.retry_state，避免和 dispatcher 双份定义
        except ImportError:
            pass

    def _extract_domain(self, img_url: str) -> str:
        """提取图片URL中的域名。"""
        if not isinstance(img_url, str) or not img_url or img_url.startswith('data:image/'):
            return ""

        parsed = urlparse(img_url)
        # 优先使用 hostname，避免 `example.com:443` 这类地址因为端口不同而无法命中同一域名策略。
        if parsed.hostname:

            return parsed.hostname.lower()
        if parsed.netloc:
            return parsed.netloc.split(':', 1)[0].lower()
        return ""


    def _record_domain_failure(self, domain: str) -> None:
        """记录域名失败次数并判断是否需要强制转base64。"""
        if not domain:
            return

        if domain not in self.domain_failure_stats:
            self.domain_failure_stats[domain] = {"consecutive": 0, "cumulative": 0}

        stats = self.domain_failure_stats[domain]
        stats["cumulative"] += 1

        last_failed_domain = self._retry_state["last_failed_domain"]
        self._last_failed_domain = last_failed_domain

        if domain == last_failed_domain:
            stats["consecutive"] += 1
        else:
            stats["consecutive"] = 1
            self._last_failed_domain = domain
            self._retry_state["last_failed_domain"] = domain

        if stats["consecutive"] >= 3 or stats["cumulative"] >= 5:
            if domain not in self.force_base64_domains:
                print(f"域名 {domain} 已触发阈值，后续将强制使用base64图片")
            self.force_base64_domains.add(domain)

    def _get_force_domains_from_img_list(self, img_list: List[str]) -> Set[str]:
        """从图片列表中提取命中的强制base64域名。"""
        matched_domains = set()
        for img_url in img_list:
            domain = self._extract_domain(img_url)
            if domain and domain in self.force_base64_domains:
                matched_domains.add(domain)
        return matched_domains

    def _convert_force_domains_to_base64(self, img_list: List[str]) -> List[str]:
        """将强制域名的图片URL转换为base64格式。"""
        matched_domains = self._get_force_domains_from_img_list(img_list)
        if not matched_domains:
            return img_list

        convert_candidates = [
            img_url
            for img_url in img_list
            if (self._extract_domain(img_url) in matched_domains) and not img_url.startswith('data:image/')
        ]

        if not convert_candidates:
            return img_list

        # 打印命中的强制域名，便于排查“域名已进集合但请求仍发URL”的问题。
        print(f"命中 force-base64 域名: {sorted(matched_domains)}")

        try:
            # 这里不能要求全量成功：某张图失败时，仍要把失败事实暴露到日志里，
            # 同时保持返回列表与原列表按位置对应，交给后续逻辑决定是否继续重试。
            converted_candidates = convert_images_to_base64(
                convert_candidates, self.image_cache, raise_on_all_failed=False
            )

        except Exception as e:
            print(f"[WARN] force-base64 批量转换异常，仍使用原始URL: {e}")
            return img_list

        if len(converted_candidates) != len(convert_candidates):
            print("[WARN] force-base64 转换结果数量异常，已回退到原始URL列表")
            return img_list

        for orig, converted in zip(convert_candidates, converted_candidates):
            if not isinstance(converted, str) or not converted.startswith('data:image/'):
                print(f"[WARN] force-base64 转换失败，仍使用原始URL: {orig}")

        converted_iter = iter(converted_candidates)
        processed_img_list = []

        for img_url in img_list:
            domain = self._extract_domain(img_url)
            if domain in matched_domains and not img_url.startswith('data:image/'):
                processed_img_list.append(next(converted_iter))
            else:
                processed_img_list.append(img_url)

        return processed_img_list

    def _select_single_retry_img_list(self, img_list: List[str]) -> List[str]:
        """重试时只保留一张图，优先保留已转成base64的图片。"""
        if not img_list:
            return img_list

        selected_img = next(
            (img for img in img_list if isinstance(img, str) and img.startswith('data:image/') and ';base64,' in img),
            img_list[0],
        )
        return [selected_img]


    def preprocess_message_info(self, message_info: Dict) -> Dict:
        """请求发送前预处理图片：命中域名策略则提前转base64。"""
        if not message_info:
            return message_info
        if not message_info.get("include_img") or not message_info.get("img_list"):
            return message_info

        message_info["img_list"] = self._convert_force_domains_to_base64(message_info["img_list"])
        return message_info

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

            for img_url in img_list:
                domain = self._extract_domain(img_url)
                if domain:
                    self._record_domain_failure(domain)

            # 命中域名策略：优先将该域名图片转为base64后重试。
            img_list = self._convert_force_domains_to_base64(img_list)
            # 这里必须同步回写 message_config，避免后续同一轮 retry 又拿到旧的 URL 列表。
            message_config["img_list"] = img_list

            # 第2次重试前，再做一次整批base64尝试。
            if api_retry_count == 1 and img_list:
                img_list = convert_images_to_base64(img_list, self.image_cache, raise_on_all_failed=False)
                # 再次回写，确保后续 retry / image_error 分支读取到的是最新状态。
                message_config["img_list"] = img_list

            # 多图重试时只保留一张，优先保留已经转成 base64 的图片。
            img_list = self._select_single_retry_img_list(img_list)
            message_config["img_list"] = img_list


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

        # 图片数量超限时，也沿用相同的单图选择策略，避免把已经转好的 base64 图丢掉。
        img_list = self._select_single_retry_img_list(message_config["img_list"])
        message_config["img_list"] = img_list


        messages = rebuild_messages_single_image(
            self.platform,
            message_config["system_prompt"],
            message_config["user_text"],
            reject_single_image=True,
            img_list=img_list,
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
        # 当前的模型信息
        base_model_info = f"Model {platform} : {model_name}"
        # print(e)

        # 获取错误信息
        error_message = self.extract_error_message(e)

        # 判断是否应该重试
        if self.should_retry_for_rate_limit(error_message):
            print_line()
            print(base_model_info)
            should_retry, updated_messages = self.handle_rate_limit_error(
                error_message, api_retry_count, messages, message_config
            )
            return should_retry, updated_messages, False

        elif self.should_retry_for_image_error(error_message, message_config):
            print_line()
            print(base_model_info)
            should_retry, updated_messages = self.handle_image_error(messages, message_config)
            return should_retry, updated_messages, False

        elif any(keyword in error_message for keyword in DEFAULT_RETRY_API_KEYWORDS):
            print_line()
            print(base_model_info)
            print("模型每日请求超过限制 或 免费额度已用完")
            return True, messages, True  # 需要重试且需要切换API密钥

        else:
            print_line()
            if error_message and 'TimeoutError' not in error_message and "原始响应中没有choices" not in error_message:
                title = "已提取到报错信息，但未匹配到任何重试场景:"
                print(title)
                print(error_message)
            else:
                title = "注意：未提取到报错信息！"
                print(title)

            # 直接重新抛出原始异常，保持异常对象的完整性
            # print(f"其他异常错误：{e}")
            raise e
