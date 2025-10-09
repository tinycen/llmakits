import json
import time
import dashscope

# 定义 dashScope 类
class DashScope :
    # DashScope api 介绍 https://help.aliyun.com/zh/model-studio/developer-reference/use-qwen-by-calling-api

    def __init__( self, api_key : str ) :

        self.api_key = api_key
        self.model = ""  # qwen-max-0125 、 qwen-vl-max-0125
        self.top_p = 0.1  # top_p越高，生成的文本更多样。反之，生成的文本更确定。
        self.top_k = 10  # integer ≤ 100 生成过程中采样候选集的大小。例如，取值为50时，仅将单次生成中得分最高的50个Token组成随机采样的候选集。取值越大，生成的随机性越高；取值越小，生成的确定性越高。
        self.stream = False  # 是否 流式输出 默认为 False ，可选为 True
        self.stream_real = False  # 是否 真的流式输出

        self.response_format = { "type" : "text" }  # 响应结果 可选值 text 、json_object

        # 任务类型 ，可选值 text 、 multi
        if self.model in [ "qwen-vl-max-0125", "qwen-vl-plus-0125" ] :
            self.task = "multi"
        else :
            self.task = "text"


    def send_message( self, messages ) :

        # 创建一个参数字典，包含固定的参数
        params = {
            "api_key"         : self.api_key,
            "model"           : self.model,
            "messages"        : messages,
            "result_format"   : 'message',
            "stream"          : self.stream,
            "response_format" : self.response_format,
        }
        result = ""
        total_tokens = 0

        max_retries = 5  # 最大重试次数
        retry_count = 0  # 当前重试次数

        while retry_count < max_retries :

            # 调用 dashscope.Generation.call 方法
            if self.task == "text" :
                response = dashscope.Generation.call( **params )
            elif self.task == "multi" :
                response = dashscope.MultiModalConversation.call( **params )
            else :
                raise ValueError( "请指定任务类型：Invalid task name. Please use 'text' or 'multi'." )

            if self.stream :
                if self.stream_real :
                    return response, total_tokens
                else :
                    for chunk in response :
                        result = chunk.output.choices[ 0 ].message.content
                    return result, total_tokens
            try :
                usage = response.usage
                if hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
                    total_tokens = usage.input_tokens + usage.output_tokens
                else:
                    total_tokens = 0
                if self.task == "multi" :
                    content = response.output.choices[ 0 ].message.content
                    if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict) and 'text' in content[0]:
                        result = content[ 0 ][ 'text' ]
                    else:
                        result = str(content) if content else ""
                else :
                    result = response.output.choices[ 0 ].message.content

                return result, total_tokens

            except :
                # print( params )
                error_message = response.message
                # 如果超出配额限制，就休息10s后重试
                if "Allocated quota exceeded, please increase your quota limit" in error_message or "Max retries exceeded with url" in error_message or "Requests rate limit exceeded, please try again later" in error_message :
                    retry_count += 1
                    print( f"请求被限流 或者 网络连接失败，正在第 {retry_count} 次重试……" )
                    time.sleep( 10 * retry_count )  # 等待一段时间后重试
                    continue
                # Input data may contain inappropriate content
                print( "消息发送Ai失败" )
                error_details = {
                    'status_code'   : response.status_code,
                    'error_code'    : response.code,
                    'error_message' : error_message
                }
                # 按照格式打印报错详细
                print( json.dumps( error_details, ensure_ascii = False, indent = 4 ) )

                raise Exception( 'Status code: %s, error code: %s, error message: %s' % (
                    response.status_code, response.code, error_message) )

        # return "error" , response
        # 报错信息参考 https://help.aliyun.com/zh/model-studio/developer-reference/error-code?spm=a2c4g.11186623.0.0.2c8565c5xIQHcr