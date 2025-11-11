import pandas as pd
from typing import Optional, Union, Any, Tuple

from ollama import chat
from openai import OpenAI
from zhipuai import ZhipuAI

from .utils.retry_handler import RetryHandler
from .message import prepare_request_data
from funcguard.printer import print_line
from funcguard.core import timeout_handler


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
        self.client: Optional[Union[OpenAI, ZhipuAI]] = None  # 由子类初始化
        self.extra_body = {}  # 额外的参数

        # 初始化重试处理器
        self.retry_handler = RetryHandler(self.platform)

    def send_message(self, messages, message_info=None):
        """发送消息的主方法"""

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
                # 处理异常和重试逻辑
                should_retry, messages, should_switch_key = self.retry_handler.handle_exception(
                    e, api_retry_count, messages, request_data, self.platform, self.model_name
                )

                if should_switch_key:
                    # 切换API密钥
                    if not self.switch_api_key():
                        print("所有API密钥都已用尽！")
                        raise Exception('API_KEY_EXHAUSTED')

                if should_retry:
                    api_retry_count += 1
                    continue
                else:
                    # 直接重新抛出原始异常，保持异常对象的完整性
                    raise e

        error_message = f"api_retry 达到最大重试次数：{max_retries}"
        print(error_message)
        raise Exception(error_message)

    def _create_chat_completion(self, messages):
        """创建聊天完成请求"""
        if self.client is None:
            raise RuntimeError("客户端未初始化")
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

        total_tokens = 0

        if stream:
            if stream_real:
                result = response
            else:
                result = timeout_handler(process_stream_response, args=(response,), execution_timeout=180)
        else:
            if self.platform == "ollama":
                result = response.message.content
                total_tokens = 0
            else:
                if response.choices:
                    if self.platform == "gitcode":
                        result = response.choices[0].delta["content"]
                    else:
                        result = response.choices[0].message.content
                    total_tokens = response.usage.total_tokens
                else:
                    # 如果没有choices，检查response是否为异常对象，如果不是则转换为异常
                    print(f"原始响应中没有choices：{response}")
                    if isinstance(response, BaseException):
                        raise response
                    else:
                        raise Exception(response)

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
            raise Exception("没有可用的API密钥")
        self.api_key = self.api_keys[0]
        if self.platform == "zhipu":
            self.client = ZhipuAI(api_key=self.api_key, timeout=self.request_timeout, max_retries=self.max_retries)
        else:
            self.client = OpenAI(
                api_key=self.api_key, base_url=self.base_url, timeout=self.request_timeout, max_retries=self.max_retries
            )

    def switch_api_key(self):
        """切换API密钥并重新初始化客户端"""
        api_keys_num = len(self.api_keys)
        if api_keys_num >= 2:
            self.api_keys.pop(0)  # 移除第一个密钥
            print(f"移除已用完的密钥，剩余 {api_keys_num-1} 个密钥")
            self._init_client()
            print_line()
            return True
        return False

    def models_df(self):
        if self.client is None:
            raise RuntimeError("客户端未初始化")

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
