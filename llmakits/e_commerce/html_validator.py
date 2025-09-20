import re


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
