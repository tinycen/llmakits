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
    校验HTML字符串是否仅包含指定的标签。
    不检查标签是否正确闭合。
    """

    # 查找所有HTML标签 (包括开始标签、结束标签和自闭合标签)
    # 这个正则表达式会匹配 <tag ...> 或 </tag> 或 <tag ... />
    found_tags = re.findall(r'<\s*/?([a-zA-Z]+)[^>]*>', html_string)

    # 将找到的标签名转换为小写集合以便比较
    found_tag_names = {tag.lower() for tag in found_tags}

    unallowed_tags = None
    # 检查所有找到的标签是否都在允许的列表中
    if found_tag_names.issubset(allowed_tags):
        print("校验成功: HTML 符合指定规范。")
        return True, unallowed_tags
    else:
        # 找出具体是哪些未被允许的标签被使用了
        unallowed_tags = found_tag_names - allowed_tags
        print(f"校验失败: 发现未被允许的标签 {unallowed_tags}")
        return False, unallowed_tags
