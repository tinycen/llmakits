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
        chinese_count = len(matches)
        if chinese_count > 0:
            print(f"发现中文字符: {repr(''.join(matches))} (数量: {chinese_count})")
            # print(f"字符详情: {[(i, repr(char), ord(char)) for i, char in enumerate(matches)]}")
        return chinese_count


# 移除字符串中的所有汉字（含扩展区）
def remove_chinese(text):
    """
    移除字符串text中的所有汉字（含扩展区）。
    """
    return regex.sub(r'\p{IsHan}+', '', text)


# 判断字符串中是否包含特殊符号
def contains_special_symbols(text, simple_check=True, support_multilingual=True):
    """
    判断字符串text中是否包含特殊符号（注意：此方法不能用于判断HTML中的特殊符号）。

    参数:
        text: 要检查的字符串
        simple_check: 是否进行简要判断，默认为True。
                    - True时返回布尔值，表示是否包含特殊符号
                    - False时返回特殊符号的数量
        support_multilingual: 是否支持多语言字符，默认为True。
                           - True时保留所有语言的字母字符（默认，支持多语言，如法语等）
                           - False时仅保留英文字母、数字和下划线

    返回:
        简要模式(True): 布尔值，表示是否包含特殊符号
        详细模式(False): 整数，表示特殊符号的数量
    """
    # 定义特殊符号的正则表达式模式
    if support_multilingual:
        # 支持多语言（默认）：使用Unicode属性匹配所有字母字符
        # 排除：.,!?;:'"()[]{}<>-_=+*/\|@#$%^&`~
        pattern = r'[^\p{L}\p{N}\s.,!?;:\'"()\[\]{}<>\-_=+*/\\|@#$%^&`~]'
    else:
        # 仅支持英语：\w只匹配英文字母、数字和下划线
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
def remove_special_symbols(text, support_multilingual=True):
    """
    移除字符串text中的所有特殊符号（注意：此方法不能用于移除HTML中的特殊符号）。

    参数:
        text: 要处理的字符串
        support_multilingual: 是否支持多语言字符，默认为True。
                           - True时保留所有语言的字母字符（默认，支持多语言，如法语等）
                           - False时仅保留英文字母、数字和下划线
    """
    # 定义特殊符号的正则表达式模式
    if support_multilingual:
        # 支持多语言（默认）：使用Unicode属性匹配所有字母字符
        # 排除：.,!?;:'"()[]{}<>-_=+*/\|@#$%^&`~
        pattern = r'[^\p{L}\p{N}\s.,!?;:\'"()\[\]{}<>\-_=+*/\\|@#$%^&`~]'
    else:
        # 仅支持英语：\w只匹配英文字母、数字和下划线
        # 排除：.,!?;:'"()[]{}<>-_=+*/\|@#$%^&`~
        pattern = r'[^\w\s.,!?;:\'"()\[\]{}<>\-_=+*/\\|@#$%^&`~]'
    return regex.sub(pattern, '', text)
