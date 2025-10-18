from llmakits.dispatcher import ModelDispatcher
from ..validators.html_validator import validate_html_fix
from ..validators.string_validator import contains_chinese
from ...message import extract_field


def generate_html(
    dispatcher: ModelDispatcher,
    product_info: str,
    generate_prompt: str,
    fix_prompt: str,
    generate_group: str,
    fix_group: str,
    allowed_tags: set[str],
    allow_chinese: bool = False,
) -> str:
    """
    生成HTML字符串
    :param dispatcher: 模型调度器
    :param product_info: 产品信息
    :param generate_prompt: 生成HTML提示词
    :param fix_prompt: 修复HTML提示词
    :param generate_group: 生成模型组名
    :param fix_group: 修复模型组名
    :param allowed_tags: 允许的HTML标签集合
    :param allow_chinese: 是否允许HTML中包含中文，默认为True
    :return: 生成的HTML字符串
    """

    def validate_func(return_message: str):
        html_string = extract_field(return_message, "html")
        if not allow_chinese:
            if contains_chinese(html_string):
                return False, None
        return True, html_string

    message_info = {"system_prompt": generate_prompt, "user_text": product_info}
    html_string, _ = dispatcher.execute_with_group(
        message_info, generate_group, format_json=True, validate_func=validate_func
    )

    des_html = validate_html_fix(dispatcher, html_string, allowed_tags, fix_group, fix_prompt)
    return des_html
