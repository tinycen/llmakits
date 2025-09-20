import re
import regex
from .html_validator import check_allowed_tags, check_tag_closing


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
        return False, '; '.join(error_messages)

    return True, ""
