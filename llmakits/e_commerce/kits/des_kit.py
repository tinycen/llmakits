from llmakits.dispatcher import ModelDispatcher
from ..validators.html_validator import validate_html_fix


def generate_html(
    dispatcher: ModelDispatcher,
    product_info: str,
    generate_prompt: str,
    fix_prompt: str,
    generate_group: str,
    fix_group: str,
    allowed_tags: set[str],
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
    :return: 生成的HTML字符串
    """
    message_info = {"system_prompt": generate_prompt, "user_text": product_info}
    result, _ = dispatcher.execute_with_group(message_info, generate_group, format_json=True)
    html_string = result["html"]
    des_html = validate_html_fix(dispatcher, html_string, allowed_tags, fix_group, fix_prompt)
    return des_html
