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
