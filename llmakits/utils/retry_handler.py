"""
重试处理组件
负责处理API请求的重试逻辑、错误处理和异常恢复
"""
import time
from typing import Dict, Tuple, Any, Optional

# 默认的重试关键词列表
DEFAULT_RETRY_KEYWORDS = [
    "Download the media resource timed out",
    "Too many requests",
    "Allocated quota exceeded, please increase your quota limit",
    "Max retries exceeded with url",
    "Requests rate limit exceeded, please try again later",
    "Failed to download multimodal content"
]


class RetryHandler:
    """处理API请求重试逻辑的组件"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.retry_keywords = DEFAULT_RETRY_KEYWORDS
    
    def prepare_request_data(self, messages: Any, message_info: Optional[Dict]) -> Tuple[Any, Dict]:
        """准备请求数据"""
        message_config = {
            "system_prompt": "",
            "user_text": "",
            "include_img": False,
            "img_list": []
        }
        
        if message_info is not None:
            message_config.update({
                "system_prompt": message_info["system_prompt"],
                "user_text": message_info["user_text"],
                "include_img": message_info.get("include_img", False),
                "img_list": message_info.get("img_list", [])
            })
            from llmakits.message import prepare_messages
            messages = prepare_messages(
                self.platform, 
                message_config["system_prompt"], 
                message_config["user_text"], 
                message_config["include_img"], 
                message_config["img_list"]
            )
        
        return messages, message_config
    
    def extract_error_message(self, e: Exception) -> str:
        """提取错误信息"""
        error_message = str(e)
        response = getattr(e, 'response', None)
        
        if response is not None:
            try:
                if hasattr(response, 'json'):
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
        return (any(error in error_message for error in image_errors) 
                and message_config["include_img"])

    def handle_rate_limit_error(self, error_message: str, api_retry_count: int, 
                               messages: Any, message_config: Dict) -> Tuple[bool, Any]:
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
        if "Failed to download multimodal content" in error_message and message_config["include_img"]:
            from llmakits.message import rebuild_messages_single_image
            img_list = message_config["img_list"]
            
            messages = rebuild_messages_single_image(
                self.platform, 
                message_config["system_prompt"], 
                message_config["user_text"], 
                message_config["include_img"],
                img_list
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
        from llmakits.message import rebuild_messages_single_image
        
        print("输入图片数量超过限制 或 图片输入格式/解析错误，正在（ 限制图片数量 = 1 ）然后重试...")
        
        messages = rebuild_messages_single_image(
            self.platform, 
            message_config["system_prompt"], 
            message_config["user_text"], 
            message_config["include_img"],
            message_config["img_list"]
        )
        
        return True, messages

    def handle_exception(self, e: Exception, api_retry_count: int, 
                        messages: Any, message_config: Dict, platform: str, 
                        model_name: str) -> Tuple[bool, Any, bool]:
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
        print(f"当前 云服务商: {platform}，模型: {model_name}")
        print(e)
        
        # 获取错误信息
        error_message = self.extract_error_message(e)
        
        # 判断是否应该重试
        if self.should_retry_for_rate_limit(error_message):
            should_retry, updated_messages = self.handle_rate_limit_error(error_message, api_retry_count, messages, message_config)
            return should_retry, updated_messages, False
        
        elif self.should_retry_for_image_error(error_message, message_config):
            should_retry, updated_messages = self.handle_image_error(messages, message_config)
            return should_retry, updated_messages, False
        
        elif "Request limit exceeded" in error_message:
            print("模型每日请求超过限制")
            return True, messages, True  # 需要重试且需要切换API密钥
        
        else:
            error_message = f"其他异常错误：{e}"
            print(error_message)
            raise Exception(error_message)


class ResponseHandler:
    """处理API响应的组件"""
    
    @staticmethod
    def handle_response(response: Any, stream: bool, stream_real: bool, 
                       timeout_handler_func: Any, process_stream_response_func: Any) -> Tuple[Any, int]:
        """处理响应"""
        total_tokens = 0
        
        if stream:
            if stream_real:
                result = response
            else:
                result = timeout_handler_func(
                    process_stream_response_func, 
                    args=(response,),
                    execution_timeout=300
                )
        else:
            result = response.choices[0].message.content
            total_tokens = response.usage.total_tokens
            
        return result, total_tokens