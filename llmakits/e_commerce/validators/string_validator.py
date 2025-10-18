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


# 判断字符串中是否包含特殊符号
def contains_special_symbols(text, simple_check=True):
    """
    判断字符串text中是否包含特殊符号（注意：此方法不能用于判断HTML中的特殊符号）。

    参数:
        text: 要检查的字符串
        simple_check: 是否进行简要判断，默认为True。
                    - True时返回布尔值，表示是否包含特殊符号
                    - False时返回特殊符号的数量

    返回:
        简要模式(True): 布尔值，表示是否包含特殊符号
        详细模式(False): 整数，表示特殊符号的数量
    """
    # 定义特殊符号的正则表达式模式，包括你提到的符号
    # \u02da 是环状音符字符，其他是中文字符
    # 这里我们排除常见的标点符号，只匹配真正的特殊符号
    # 排除：.,!?;:'"()[]{}<>-_=+*/\|@#$%^&`~
    pattern = r'[^\w\s.,!?;:\'"()\[\]{}<>\-_=+*/\\|@#$%^&`~]'

    if simple_check:
        return bool(regex.search(pattern, text))
    else:
        # 查找所有特殊符号并返回数量
        matches = regex.findall(pattern, text)
        print(f"发现特殊符号: {''.join(matches)}")
        return len(matches)


# 移除字符串中的所有特殊符号
def remove_special_symbols(text):
    """
    移除字符串text中的所有特殊符号（注意：此方法不能用于移除HTML中的特殊符号）。
    """
    # 定义特殊符号的正则表达式模式
    # 排除常见的标点符号，只匹配真正的特殊符号
    # 排除：.,!?;:'"()[]{}<>-_=+*/\|@#$%^&`~
    pattern = r'[^\w\s.,!?;:\'"()\[\]{}<>\-_=+*/\\|@#$%^&`~]'
    return regex.sub(pattern, '', text)
