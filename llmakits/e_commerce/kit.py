from typing import List
from .validators.string_validator import contains_chinese
from ..message import extract_field
from llmakits.dispatcher import ModelDispatcher


def translate_options(
    dispatcher: ModelDispatcher, title: str, options: List[str], to_lang: str, group_name: str, system_prompt: str
):
    """
    翻译选项，并确保输出列表长度与输入一致。

    :param title: 商品标题
    :param options: 原始选项列表
    :param to_lang: 目标语言
    :param group_name: 模型组名称
    :param system_prompt: 系统提示语
    :return: 翻译后的选项列表
    """
    # 首先检测源语言是否包含中文，如果不包含中文，就直接返回原语言
    if not contains_chinese(str(options)):
        return options, 0

    user_text = f"title:{title},options:{options},请翻译为:{to_lang}语言"

    # 验证条件：校验返回的 options 长度是否与原 options 一致
    def validate_func(return_message):
        """
        说明：validate_func 作为闭包引用了外部的 options 变量，
        即使 send_message 只传递 return_message 参数，这里依然可以访问 options。
        返回：(验证是否通过, 验证通过的值)
        """
        translated_options = extract_field(return_message, "options")
        # 只有长度相等，且不存在重复值，才算验证通过
        if len(options) == len(translated_options) == len(set(translated_options)):
            return True, translated_options
        else:
            return False, None

    return_message, _ = dispatcher.execute_with_group(  # type: ignore
        {"user_text": user_text, "system_prompt": system_prompt},
        group_name,
        format_json=True,
        validate_func=validate_func,
    )
    # 由于validate_func返回验证通过的值，这里直接使用return_message
    return return_message
