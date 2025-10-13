import re


def base_symbol(text: str) -> list[str]:
    """
    符号分词器，将文本按英文逗号、中文逗号、空格，分割为单词列表。

    Args:
        text: 输入的文本字符串

    Returns:
        分割后的单词列表，每个单词都是一个字符串
    """
    # 使用正则表达式分割单词，支持空格和逗号分隔
    # 正则表达式 r'[,，\s]+' 工作原理：
    # - [,，\s]+ 匹配一个或多个连续的字符，这些字符可以是：
    #   - , 英文逗号
    #   - ， 中文逗号
    #   - \s 任何空白字符（包括空格、制表符、换行符等）
    # - + 表示匹配一个或多个这样的字符
    # 这样可以处理同时存在逗号和空格的情况，如"手机, 电脑 平板"

    words = re.split(r'[,，\s]+', text.strip())
    # 去除空字符串并去重
    words = list(set(filter(None, words)))
    return words
