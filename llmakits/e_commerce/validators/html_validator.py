import re
from ...dispatcher import ModelDispatcher


def check_allowed_tags(html_string: str, allowed_tags: set[str]):
    """
    检查HTML字符串中的标签是否都在允许的标签列表中。

    Args:
        html_string: 要检查的HTML字符串
        allowed_tags: 允许使用的标签集合

    Returns:
        set: 未被允许的标签名集合
    """
    # 查找所有HTML标签 (包括开始标签、结束标签和自闭合标签)
    # 这个正则表达式会匹配 <tag ...> 或 </tag> 或 <tag ... />
    found_tags = re.findall(r'<\s*/?([a-zA-Z]+)[^>]*>', html_string)

    # 将找到的标签名转换为小写集合以便比较
    found_tag_names = {tag.lower() for tag in found_tags}

    # 检查所有找到的标签是否都在允许的列表中
    unallowed_tags = found_tag_names - allowed_tags

    return unallowed_tags


def check_tag_closing(html_string: str):
    """
    检查HTML字符串中的标签是否正确闭合。

    Args:
        html_string: 要检查的HTML字符串

    Returns:
        set: 未正确闭合的标签名集合
    """
    # 自闭合标签列表
    self_closing_tags = {
        'br',
        'hr',
        'img',
        'input',
        'meta',
        'link',
        'area',
        'base',
        'col',
        'embed',
        'source',
        'track',
        'wbr',
    }

    # 匹配开始标签、结束标签和自闭合标签
    tag_pattern = r'<\s*(/?)([a-zA-Z]+)[^>]*>'
    tags = re.findall(tag_pattern, html_string)

    tag_stack = []
    unclosed_tags = set()

    for is_closing, tag_name in tags:
        tag_name = tag_name.lower()

        # 跳过自闭合标签
        if tag_name in self_closing_tags:
            continue

        if not is_closing:  # 开始标签
            tag_stack.append(tag_name)
        else:  # 结束标签
            if tag_stack and tag_stack[-1] == tag_name:
                tag_stack.pop()
            else:
                # 标签未正确闭合
                unclosed_tags.add(tag_name)

    # 栈中剩余的标签都是未闭合的
    unclosed_tags.update(tag_stack)
    return unclosed_tags


def validate_html(html_string: str, allowed_tags: set[str]):
    """
    校验HTML字符串是否仅包含指定的标签，并检查标签是否正确闭合。

    Args:
        html_string: 要校验的HTML字符串
        allowed_tags: 允许使用的标签集合

    Returns:
        tuple: (是否校验通过, 错误信息)
               如果校验通过，返回(True, "")
               如果校验失败，返回(False, 错误描述字符串)
    """

    # 构建错误信息
    error_messages = []

    # 检查标签是否被允许（仅当 allowed_tags 不为空时）
    if allowed_tags:
        unallowed_tags = check_allowed_tags(html_string, allowed_tags)
        if unallowed_tags:
            error_messages.append(f"发现未被允许的标签: {', '.join(sorted(unallowed_tags))}")

    # 检查标签闭合情况
    unclosed_tags = check_tag_closing(html_string)

    if unclosed_tags:
        error_messages.append(f"发现未正确闭合的标签: {', '.join(sorted(unclosed_tags))}")

    # 返回结果
    if error_messages:
        print(error_messages)
        return False, '; '.join(error_messages)

    return True, ""


def validate_html_fix(
    dispatcher: ModelDispatcher, html_string: str, allowed_tags: set[str], group_name: str, system_prompt: str
):
    """
    校验HTML字符串是否合规，并修复不允许的标签。
    """
    is_valid, error_messages = validate_html(html_string, allowed_tags)
    fixed_num = 0
    max_attempts = 5
    while not is_valid and fixed_num < max_attempts:
        fixed_num += 1
        message_info = {
            "system_prompt": system_prompt,
            "user_text": f"allowed_tags:{allowed_tags},html:{html_string},error_messages:{error_messages}",
        }
        return_message, _ = dispatcher.execute_with_group(message_info, group_name, format_json=True)
        html_string = return_message["html"]
        is_valid, error_messages = validate_html(html_string, allowed_tags)

    # 如果达到最大尝试次数仍未验证通过，抛出异常
    if not is_valid:
        raise Exception(f"HTML验证失败，已达到最大尝试修复次数({max_attempts})\n最后一次错误: {error_messages}")

    return html_string
