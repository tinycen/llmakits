from ...message import extract_field
from ...dispatcher import ModelDispatcher
from ..validators import remove_chinese


def check_title(title: str, max_length: int, min_length: int = 10, min_word: int = 2) -> bool:
    """
    检查标题是否符合长度和单词数的要求。

    :param title: 标题
    :param max_length: 最大允许长度
    :param min_length: 最小允许长度
    :param min_word: 最少单词数
    :return: 是否符合条件
    """
    title_length = len(title)
    word_count = len(title.split())
    return min_length <= title_length <= max_length and word_count >= min_word


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


def generate_title(
    dispatcher: ModelDispatcher,
    title: str,
    product_info: str,
    system_prompt: str,
    group_name: str,
    min_length: int = 10,
    max_length: int = 225,
    min_word: int = 2,
    max_attempts: int = 3,
    allow_chinese: bool = False,
) -> str:
    """
    生成商品标题，如果不符合要求则进行修改。

    :param dispatcher: 模型调度器
    :param title: 原始标题
    :param product_info: 商品信息
    :param system_prompt: 系统提示语
    :param group_name: 模型组名称
    :param min_length: 最小允许长度
    :param max_length: 最大允许长度
    :param min_word: 最少单词数
    :param max_attempts: 最大尝试次数
    :param allow_chinese: 是否允许中文标题
    :return: 符合要求的标题
    """
    print("检测商品标题……")
    if not allow_chinese:
        title = remove_chinese(title)
    if title and check_title(title, max_length, min_length, min_word):
        return title

    def build_message_info(cur_title, title_length, try_max_length):
        if cur_title == "":
            user_text = product_info
        else:
            user_text = (
                f"title:{cur_title},长度={title_length}不合格，请你修改，长度范围为{min_length}~{try_max_length}"
            )
        return {"system_prompt": system_prompt, "user_text": user_text}

    def validate_func(return_message: str):
        best_title = extract_field(return_message, "title")
        return True, best_title

    best_title = title
    for attempt in range(1, max_attempts + 1):

        print(f"第 {attempt} 次修改中……")
        title_length = len(best_title)
        if title_length > max_length:
            try_max_length -= 5  # 每次尝试减少最大长度限制
        else:
            try_max_length = max_length
        message_info = build_message_info(best_title, title_length, try_max_length)
        best_title, _ = dispatcher.execute_with_group(message_info, group_name, format_json=True, validate_func=validate_func)  # type: ignore
        if not allow_chinese:
            best_title = remove_chinese(best_title)
        if check_title(best_title, max_length, min_length, min_word):  # type: ignore
            return best_title  # type: ignore

    print("程序性缩减标题……")
    return shorten_title(best_title, max_length)
