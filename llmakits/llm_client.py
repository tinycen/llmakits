import pandas as pd
from typing import Optional, Union

from openai import OpenAI
from zhipuai import ZhipuAI

from llmakits.utils.retry_handler import RetryHandler, ResponseHandler

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
        messages, request_data = self.retry_handler.prepare_request_data(messages, message_info)

        # 执行重试逻辑
        max_retries = 5
        api_retry_count = 0

        while api_retry_count < max_retries:
            try:
                # 创建聊天完成请求
                response = self._create_chat_completion(messages)

                # 处理响应
                result, total_tokens = ResponseHandler.handle_response(
                    response, self.stream, self.stream_real, timeout_handler, process_stream_response
                )
                return result, total_tokens

            except Exception as e:
                # 处理异常和重试逻辑
                should_retry, messages, should_switch_key = self.retry_handler.handle_exception(
                    e, api_retry_count, messages, request_data, self.platform, self.model_name
                )

                if should_switch_key:
                    # 切换API密钥
                    if not self.switch_api_key():
                        print("所有API密钥都已用尽，无法继续")
                        raise Exception('API_KEY_EXHAUSTED')

                if should_retry:
                    api_retry_count += 1
                    continue
                else:
                    raise

        raise Exception(f"api_retry 达到最大重试次数：{max_retries}")

    def _create_chat_completion(self, messages):
        """创建聊天完成请求"""
        if self.client is None:
            raise RuntimeError("客户端未初始化")
        return self.client.chat.completions.create(
            messages=messages,  # type: ignore
            model=self.model_name,
            temperature=self.temperature,
            top_p=self.top_p,
            stream=self.stream,
            **self.extra_body,  # 传递额外的参数
        )


# 定义 BaseOpenai 类
class BaseOpenai(BaseClient):
    def __init__(self, platform, base_url, api_keys, model_name, response_format="json"):
        super().__init__(platform, model_name)
        self.base_url = base_url
        self.api_keys = api_keys

        # 处理流式输出
        if platform == "modelscope":
            if model_name in ["Qwen/QwQ-32B", "Qwen/QVQ-72B-Preview", "Qwen/Qwen3-235B-A22B", "Qwen/Qwen3-32B"]:
                self.stream = True
                self.stream_real = False

            if model_name in ["Qwen/Qwen3-235B-A22B", "Qwen/Qwen3-32B"]:
                extra_body = {"enable_thinking": False}
                self.extra_body = {"extra_body": extra_body}

        # 处理 response_format
        if platform == "zhipu":
            if response_format == "json":
                self.response_format = {"type": "json_object"}
            else:
                self.response_format = {"type": "text"}
            self.extra_body = {"response_format": self.response_format}

        self.platform = platform

        # 初始化客户端
        self._init_client()

    def _init_client(self):
        """初始化客户端，使用第1个密钥"""
        if not self.api_keys:
            raise Exception("没有可用的API密钥")
        self.api_key = self.api_keys[0]
        if self.platform == "zhipu":
            self.client = ZhipuAI(api_key=self.api_key)
        else:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def switch_api_key(self):
        """切换API密钥并重新初始化客户端"""
        api_keys_num = len(self.api_keys)
        if api_keys_num >= 2:
            self.api_keys.pop(0)  # 移除第一个密钥
            print(f"移除已用完的密钥，剩余 {api_keys_num-1} 个密钥")
            self._init_client()
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
