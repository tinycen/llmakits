import regex


# 判断字符串中是否包含汉字
def contains_chinese(text):
    """
    判断字符串text中是否包含所有汉字（含扩展区）。
    """
    # 汉字的 Unicode 脚本是 Han
    return bool(regex.search(r'\p{IsHan}', text))


# 移除字符串中的所有汉字（含扩展区）
def remove_chinese(text):
    """
    移除字符串text中的所有汉字（含扩展区）。
    """
    return regex.sub(r'\p{IsHan}+', '', text)