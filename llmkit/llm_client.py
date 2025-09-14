import time
import pandas as pd

from openai import OpenAI
from zhipuai import ZhipuAI

from llmkit.message import convert_to_json, prepare_messages
from llm_utils.args import default_api_keys

from funcguard.core import timeout_handler


# 发送消息
def send_message(message_info, llm_models, format_json=False, validate_func=None):
    retry_count = 0
    models_num = len(llm_models)

    for idx, model_info in enumerate(llm_models):
        base_model_info = f"{idx+1}/{models_num} Model {model_info['sdk_name']} : {model_info.get('model_name', 'unknown_model')}"
        try:
            return_message, total_tokens = model_info["model"].send_message([], message_info)
            if format_json:
                return_message = convert_to_json(return_message)
            # 新增：如果有校验函数，校验不通过则继续下一个模型
            if validate_func is not None and not validate_func(return_message):
                print(base_model_info)
                print("输出结果：条件校验失败, trying next model ...")
                retry_count += 1
                continue
            return return_message, total_tokens, retry_count
        except Exception as e:
            print(base_model_info)
            if idx < models_num - 1:
                print("model failed, trying next model ...")
                retry_count += 1
                continue
            else:
                raise e  # 如果所有模型都失败则抛出异常

    # 如果所有模型都失败
    raise Exception("All models failed to send message.")


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
        self.model = model_name
        self.model_name = model_name
        self.platform = platform  # 云服务商平台，由子类传入
        self.temperature = 0.4
        self.top_p = 0.1
        self.stream = False  # 是否流式输出，默认为 False，可选为 True
        self.stream_real = False  # 是否真的流式输出
        self.client = None  # 由子类初始化
        self.extra_body = {}  # 额外的参数

        self.retry_keywords = [
            "Download the media resource timed out",
            "Too many requests",
            "Allocated quota exceeded, please increase your quota limit",
            "Max retries exceeded with url",
            "Requests rate limit exceeded, please try again later",
            "Failed to download multimodal content"
        ]

    def send_message(self, messages, message_info=None):
        if message_info is not None:
            system_prompt = message_info["system_prompt"]
            user_text = message_info["user_text"]
            include_img = message_info.get("include_img", False)
            img_list = message_info.get("img_list", [])
            messages = prepare_messages(self.platform, system_prompt, user_text, include_img, img_list)

        total_tokens = 0
        max_retries = 5  # 最大重试次数
        retry_count = 0  # 当前重试次数

        while retry_count < max_retries:
            try:
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stream=self.stream,
                    **self.extra_body  # 获取特定的额外参数
                )

                if self.stream:
                    if self.stream_real:
                        result = response
                    else:
                        result = timeout_handler(process_stream_response, args=(response,),
                                                  execution_timeout=300)
                else:
                    result = response.choices[0].message.content
                    total_tokens = response.usage.total_tokens

                return result, total_tokens

            except Exception as e:
                # 打印当前的模型信息
                print(f"当前 云服务商: {self.platform}，模型: {self.model_name}")
                print(e)
                res = e.response.json()
                error = res.get("error", res.get("errors", ""))
                # 智谱Ai报错信息 {"error":{"code":"1210","message":"输入图片数量超过限制"}}
                # error_code = error["code"]
                error_message = error.get("message", "")

                # 优化后的限流/网络错误判断
                if any(keyword in error_message for keyword in self.retry_keywords):
                    retry_count += 1
                    print(f"请求被限流 或者 网络连接失败，正在第 {retry_count} 次重试……")
                    if "Failed to download multimodal content" in error_message and message_info is not None:
                        if len(img_list) == 1:
                            print("异常：图片数量 = 1，仍报异常：下载失败")
                            print(f"img_list : {img_list}")
                            raise Exception("异常：图片数量 = 1，下载失败")
                        # 重新构造messages
                        messages = prepare_messages(self.platform, system_prompt, user_text, include_img,
                                                     [img_list[0]])
                    else:
                        time.sleep(10 * retry_count)  # 等待一段时间后重试
                    continue

                elif (
                        "输入图片数量超过限制" in error_message or "图片输入格式/解析错误" in error_message) and message_info is not None:
                    print("输入图片数量超过限制 或 图片输入格式/解析错误，正在（ 限制图片数量 = 1 ）然后重试...")
                    if len(img_list) == 1:
                        print("异常：图片数量 = 1，未超出限制")
                        print(f"img_list : {img_list}")
                        raise Exception("异常：图片数量 = 1，未超出限制")

                    # 重新构造messages
                    messages = prepare_messages(self.platform, system_prompt, user_text, include_img,
                                                 [img_list[0]])
                    retry_count += 1
                    continue

                elif "Request limit exceeded" in error_message:  # modelscope 部分模型 每日请求 有限制
                    print("模型每日请求超过限制.")
                    raise Exception('Request limit exceeded')
                else:
                    error_message = f"其他异常错误：{e}"
                    print(error_message)
                    raise Exception(error_message)


# 定义 BaseOpenai 类
class BaseOpenai(BaseClient):
    def __init__(self, platform, api_key="", model_name="", response_format="json"):
        super().__init__(platform, model_name)
        api_keys = default_api_keys["Api_keys"]
        default_api_key = api_keys[platform]

        self.base_url = default_api_key["base_url"]
        base_api_key = default_api_key["api_key"]

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

        if api_key == "":
            self.api_key = base_api_key
        else:
            self.api_key = api_key

        self.platform = platform

        # 初始化客户端
        if self.platform == "zhipu":
            self.client = ZhipuAI(api_key=self.api_key)
        else:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def models_df(self):
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