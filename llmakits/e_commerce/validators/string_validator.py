import regex


# 判断字符串中是否包含汉字
def contains_chinese(text, simple_check=True):
    """
    判断字符串text中是否包含所有汉字（含扩展区）。

    参数:
        text: 要检查的字符串
        simple_check: 是否进行简要判断，默认为True。
                    - True时返回布尔值，表示是否包含汉字
                    - False时返回中文字符的数量

    返回:
        简要模式(True): 布尔值，表示是否包含汉字
        详细模式(False): 整数，表示中文字符的数量
    """
    # 汉字的 Unicode 脚本是 Han
    if simple_check:
        return bool(regex.search(r'\p{IsHan}', text))
    else:
        # 查找所有汉字并返回数量
        matches = regex.findall(r'\p{IsHan}', text)
        print(f"发现中文字符: {''.join(matches)}")
        return len(matches)


# 移除字符串中的所有汉字（含扩展区）
def remove_chinese(text):
    """
    移除字符串text中的所有汉字（含扩展区）。
    """
    return regex.sub(r'\p{IsHan}+', '', text)
