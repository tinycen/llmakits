"""
重试处理组件
负责处理API请求的重试逻辑、错误处理和异常恢复
"""
import time
from typing import Dict, List, Tuple, Any, Optional

# 默认的重试关键词列表
DEFAULT_RETRY_KEYWORDS = [
    "Download the media resource timed out",
    "Too many requests",
    "Allocated quota exceeded, please increase your quota limit",
    "Max retries exceeded with url",
    "Requests rate limit exceeded, please try again later",
    "Failed to download multimodal content"
]

# 延迟导入以避免循环依赖
def get_prepare_messages():
    from llmkit.message import prepare_messages
    return prepare_messages


class RetryHandler:
    """处理API请求重试逻辑的组件"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.retry_keywords = DEFAULT_RETRY_KEYWORDS
    
    def prepare_request_data(self, messages: Any, message_info: Optional[Dict]) -> Tuple[Any, Dict]:
        """准备请求数据"""
        request_data = {
            "system_prompt": "",
            "user_text": "",
            "include_img": False,
            "img_list": []
        }
        
        if message_info is not None:
            request_data.update({
                "system_prompt": message_info["system_prompt"],
                "user_text": message_info["user_text"],
                "include_img": message_info.get("include_img", False),
                "img_list": message_info.get("img_list", [])
            })
            prepare_messages = get_prepare_messages()
            messages = prepare_messages(
                self.platform, 
                request_data["system_prompt"], 
                request_data["user_text"], 
                request_data["include_img"], 
                request_data["img_list"]
            )
        
        return messages, request_data
    
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
    
    def should_retry_for_image_error(self, error_message: str, request_data: Dict) -> bool:
        """判断是否因为图片错误而重试"""
        image_errors = ["输入图片数量超过限制", "图片输入格式/解析错误"]
        return (any(error in error_message for error in image_errors) 
                and request_data["include_img"])
    
    def handle_rate_limit_error(self, error_message: str, retry_count: int, 
                               messages: Any, request_data: Dict) -> Tuple[bool, Any]:
        """处理限流错误"""
        print(f"请求被限流 或者 网络连接失败，正在第 {retry_count + 1} 次重试……")
        
        if "Failed to download multimodal content" in error_message and request_data["include_img"]:
            img_list = request_data["img_list"]
            if len(img_list) == 1:
                print("异常：图片数量 = 1，仍报异常：下载失败")
                print(f"img_list : {img_list}")
                raise Exception("异常：图片数量 = 1，下载失败")
            
            # 重新构造messages，只使用第一张图片
            prepare_messages = get_prepare_messages()
            messages = prepare_messages(
                self.platform, 
                request_data["system_prompt"], 
                request_data["user_text"], 
                request_data["include_img"],
                [img_list[0]]
            )
        else:
            time.sleep(10 * (retry_count + 1))  # 等待一段时间后重试
        
        return True, messages
    
    def handle_image_error(self, error_message: str, retry_count: int, 
                          messages: Any, request_data: Dict) -> Tuple[bool, Any]:
        """处理图片相关错误"""
        print("输入图片数量超过限制 或 图片输入格式/解析错误，正在（ 限制图片数量 = 1 ）然后重试...")
        
        img_list = request_data["img_list"]
        if len(img_list) == 1:
            print("异常：图片数量 = 1，未超出限制")
            print(f"img_list : {img_list}")
            raise Exception("异常：图片数量 = 1，未超出限制")

        # 重新构造messages，只使用第一张图片
        prepare_messages = get_prepare_messages()
        messages = prepare_messages(
            self.platform, 
            request_data["system_prompt"], 
            request_data["user_text"], 
            request_data["include_img"],
            [img_list[0]]
        )
        
        return True, messages
    
    def handle_exception(self, e: Exception, retry_count: int, max_retries: int, 
                        messages: Any, request_data: Dict, platform: str, 
                        model_name: str) -> Tuple[bool, Any]:
        """处理异常和重试逻辑"""
        # 打印当前的模型信息
        print(f"当前 云服务商: {platform}，模型: {model_name}")
        print(e)
        
        # 获取错误信息
        error_message = self.extract_error_message(e)
        
        # 判断是否应该重试
        if self.should_retry_for_rate_limit(error_message):
            return self.handle_rate_limit_error(error_message, retry_count, messages, request_data)
        
        elif self.should_retry_for_image_error(error_message, request_data):
            return self.handle_image_error(error_message, retry_count, messages, request_data)
        
        elif "Request limit exceeded" in error_message:
            print("模型每日请求超过限制.")
            raise Exception('Request limit exceeded')
        
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