import httpx
import pandas as pd
from typing import Optional, Union, Any, Tuple

from ollama import chat
from openai import OpenAI
from zai import ZhipuAiClient

from .utils.retry_handler import RetryHandler
from .utils.normalize_error import ResponseError
from .message import prepare_request_data
from funcguard import print_line, timeout_handler


# 定义基类
def process_stream_response(response):
    result = ""
    for chunk in response:
        result += chunk.choices[0].delta.content
    # 思考：reasoning_chunk = chunk.choices[0].delta.reasoning_content
    # 回答：answer_chunk = chunk.choices[0].delta.content
    return result


class BaseClient:
    def __init__(self, platform: str, model_name: str):
        # 初始化模型参数
        self.model_name = model_name
        self.platform = platform  # 云服务商平台，由子类传入
        self.temperature = 0.4
        self.top_p = 0.1
        self.stream = False  # 是否流式输出，默认为 False，可选为 True
        self.stream_real = False  # 是否真的流式输出
        self.client: Optional[Union[OpenAI, ZhipuAiClient]] = None  # 由子类初始化
        self.extra_body = {}  # 额外的参数

        # 初始化重试处理器
        self.retry_handler = RetryHandler(self.platform, self.model_name)

    def switch_api_key(self):
        """切换API密钥（子类可覆盖）"""
        return False

    def send_message(self, messages, message_info=None):
        """发送消息的主方法"""
        if message_info is not None:
            message_info = self.retry_handler.preprocess_message_info(message_info)

        # 准备请求数据
        messages, request_data = prepare_request_data(self.platform, messages, message_info)

        # 执行重试逻辑
        max_retries = 4  # 考虑到 需要切换api key , 以及可能面临图片异常，设置为 4 比较合理
        api_retry_count = 0

        while api_retry_count < max_retries:

            try:
                # 创建聊天完成请求
                response = timeout_handler(self._create_chat_completion, args=(messages,), execution_timeout=180)

                # 处理响应
                result, total_tokens = self._handle_response(response, self.stream, self.stream_real)
                return result, total_tokens

            except Exception as e:

                if not isinstance(e, ResponseError):
                    if "TimeoutError" in str(e):
                        error_tag = "响应超时"
                    else:
                        error_tag = "响应异常"
                    response_error = ResponseError(self.platform, self.model_name, exception=e, error_tag=error_tag)
                else:
                    response_error = e

                # 处理异常和重试逻辑
                should_retry, messages, should_switch_key = self.retry_handler.handle_exception(
                    response_error, api_retry_count, messages, request_data
                )

                if should_switch_key:
                    # 切换API密钥
                    if not self.switch_api_key():
                        error_tag = "所有API密钥都已用尽"
                        exception = Exception("API_KEY_EXHAUSTED")
                        response_error = ResponseError(
                            self.platform, self.model_name, exception=exception, error_tag=error_tag
                        )
                        response_error.skip_report = True
                        raise response_error

                if should_retry:
                    api_retry_count += 1
                    continue

                raise response_error

        error_tag = "api_retry达到最大重试次数"
        exception = Exception(f"API_RETRY_REACHED, MAXIMUM_RETRIES: {max_retries}")
        response_error = ResponseError(self.platform, self.model_name, exception=exception, error_tag=error_tag)
        response_error.skip_report = True
        raise response_error

    def _create_chat_completion(self, messages):
        """创建聊天完成请求"""
        if self.client is None:
            error_tag = "客户端未初始化"
            error_message = f"client 客户端未初始化，无法执行 _create_chat_completion ：{self.platform}"
            response_error = ResponseError(
                self.platform, self.model_name, exception=Exception(error_message), error_tag=error_tag
            )
            raise response_error

        if self.platform == "ollama":
            # https://docs.ollama.com/api#generate-request-with-options
            return chat(
                messages=messages,
                model=self.model_name,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                },
                **self.extra_body,  # 传递额外的参数
            )
        else:
            return self.client.chat.completions.create(
                messages=messages,  # type: ignore
                model=self.model_name,
                temperature=self.temperature,
                top_p=self.top_p,
                stream=self.stream,
                **self.extra_body,  # 传递额外的参数
            )

    def _handle_response(
        self,
        response: Any,
        stream: bool,
        stream_real: bool,
    ) -> Tuple[Any, int]:
        """处理响应"""

        # 非流式响应，直接获取 content
        if isinstance(response, str):
            error_tag = "response类型是字符串"
            response_error = ResponseError(
                self.platform, self.model_name, exception=Exception(response), error_tag=error_tag
            )
            raise response_error

        total_tokens = 0

        if stream:
            if stream_real:
                result = response
            else:
                try:
                    # 使用 funcguard 处理超时，超时会抛出异常 TimeoutError
                    result = timeout_handler(process_stream_response, args=(response,), execution_timeout=180)
                except Exception as e:
                    if "TimeoutError" in str(e):
                        error_tag = "流式响应_超时"
                    else:
                        error_tag = "流式响应_异常"
                    response_error = ResponseError(self.platform, self.model_name, exception=e, error_tag=error_tag)
                    response_error.skip_report = True
                    raise response_error
        else:
            if self.platform == "ollama":
                result = response.message.content
            else:

                if hasattr(response, 'choices') and response.choices:
                    try:
                        result = response.choices[0].message.content
                    except:
                        # self.platform == "gitcode"，部分情况适用
                        result = response.choices[0].delta["content"]

                    if response.usage is not None:
                        total_tokens = response.usage.total_tokens

                else:
                    # 保留原有日志，便于问题排查
                    error_tag = "原始响应中没有choices"

                    # 保持原有语义：如果本身是异常对象，则直接抛出原异常
                    if isinstance(response, BaseException):
                        exception = response
                    else:
                        exception = Exception(response)
                    response_error = ResponseError(
                        self.platform, self.model_name, exception=exception, error_tag=error_tag
                    )

                    raise response_error

        return result, total_tokens


# 定义 BaseOpenai 类
class BaseOpenai(BaseClient):

    def __init__(self, platform, base_url, api_keys, model_name, stream=False, stream_real=False, extra_body=None):
        super().__init__(platform, model_name)
        self.base_url = base_url
        self.api_keys = api_keys
        self.request_timeout = 150  # 新增：API 请求超时时间
        self.max_retries = 3  # 新增：API 请求超时时间

        self.platform = platform
        self.stream = stream
        self.stream_real = stream_real

        # 配置 extra_body 参数
        if extra_body is not None:
            self.extra_body = extra_body

        # 初始化客户端
        self._init_client()

    def _init_client(self):
        """初始化客户端，使用第1个密钥"""
        if not self.api_keys:
            error_tag = "没有可用的API密钥"
            error_message = f"没有可用的API密钥，无法执行 _init_client ：{self.platform}"
            response_error = ResponseError(
                self.platform, self.model_name, exception=Exception(error_message), error_tag=error_tag
            )
            raise response_error

        self.api_key = self.api_keys[0]
        if self.platform == "zhipu":
            # 新版 zai-sdk 使用 httpx 客户端配置超时
            httpx_client = httpx.Client(timeout=self.request_timeout)
            self.client = ZhipuAiClient(api_key=self.api_key, http_client=httpx_client)
        else:
            self.client = OpenAI(
                api_key=self.api_key, base_url=self.base_url, timeout=self.request_timeout, max_retries=self.max_retries
            )

    def switch_api_key(self):
        """切换API密钥并重新初始化客户端"""
        api_keys_num = len(self.api_keys)
        if api_keys_num >= 2:
            self.api_keys.pop(0)  # 移除第一个密钥
            print(f"移除已用完的密钥，剩余 {api_keys_num - 1} 个密钥")
            self._init_client()
            # print_line()
            return True
        return False

    def models_df(self):
        if self.client is None:
            error_tag = "客户端未初始化"
            error_message = f"client 客户端未初始化，无法执行 models_df ：{self.platform}"
            response_error = ResponseError(
                self.platform, self.model_name, exception=Exception(error_message), error_tag=error_tag
            )
            raise response_error

        # 获取模型列表
        models_page = self.client.models.list()

        # 提取模型数据
        models_data = [
            {
                'id': model.id,
                'created': model.created,
            }
            for model in models_page.data
        ]

        # 创建DataFrame
        df = pd.DataFrame(models_data)
        # 将created时间戳转换为日期
        df['created_date'] = pd.to_datetime(df['created'], unit='s').dt.strftime('%Y-%m-%d')
        # 移除旧的created列
        df = df.drop('created', axis=1)  # axis=1表示删除列
        # 按照created_date降序排序
        df = df.sort_values('created_date', ascending=False).reset_index(drop=True)

        return df
