import re
import regex


# 判断字符串中是否包含汉字
def contains_chinese(s):
    """
    判断字符串s中是否包含所有汉字（含扩展区）。
    """
    # 汉字的 Unicode 脚本是 Han
    return bool(regex.search(r'\p{IsHan}', s))


# 移除字符串中的所有汉字（含扩展区）
def remove_chinese(s):
    """
    移除字符串s中的所有汉字（含扩展区）。
    """
    return regex.sub(r'\p{IsHan}+', '', s)


# 程序化缩减标题
def shorten_title(title, target_length=100, split_char=" "):
    # 第1次 去除英文逗号
    title = title.replace(",", "")

    # 如果长度已经满足要求，直接返回
    if len(title) <= target_length:
        return title

    # 第2次 舍弃单词-缩减
    words = title.split(split_char)
    # 使用列表切片，避免频繁的字符串拼接操作
    while len(" ".join(words)) > target_length:
        words.pop()  # 移除最后一个单词

    # 返回缩减后的标题
    return " ".join(words)


# 校验HTML字符串是否合规
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

    # 查找所有HTML标签 (包括开始标签、结束标签和自闭合标签)
    # 这个正则表达式会匹配 <tag ...> 或 </tag> 或 <tag ... />
    found_tags = re.findall(r'<\s*/?([a-zA-Z]+)[^>]*>', html_string)

    # 将找到的标签名转换为小写集合以便比较
    found_tag_names = {tag.lower() for tag in found_tags}

    # 检查所有找到的标签是否都在允许的列表中
    unallowed_tags = found_tag_names - allowed_tags

    # 检查标签闭合情况
    unclosed_tags = check_tag_closing(html_string)

    # 构建错误信息
    error_messages = []

    if unallowed_tags:
        error_messages.append(f"发现未被允许的标签: {', '.join(sorted(unallowed_tags))}")

    if unclosed_tags:
        error_messages.append(f"发现未正确闭合的标签: {', '.join(sorted(unclosed_tags))}")

    # 返回结果
    if error_messages:
        return False, '; '.join(error_messages)

    return True, ""


# 检查HTML标签是否闭合
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
