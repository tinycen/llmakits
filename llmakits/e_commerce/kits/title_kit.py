from ..tools import shorten_title
from llmakits.message import extract_field
from llmakits.dispatcher import ModelDispatcher


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


def generate_title(
    dispatcher: ModelDispatcher,
    title: str,
    group_name: str,
    system_prompt: str,
    max_length: int = 225,
    min_length: int = 10,
    min_word: int = 2,
    max_attempts: int = 3,
) -> str:
    """
    生成商品标题，如果不符合要求则进行修改。

    :param dispatcher: 模型调度器
    :param title: 原始标题
    :param group_name: 模型组名称
    :param system_prompt: 系统提示语
    :param max_length: 最大允许长度
    :param min_length: 最小允许长度
    :param min_word: 最少单词数
    :param max_attempts: 最大尝试次数
    :return: 符合要求的标题
    """
    print("检测商品标题……")

    if check_title(title, max_length, min_length, min_word):
        return title

    def build_message_info(cur_title, title_length):
        user_text = f"title:{cur_title},长度={title_length}不合格，请你修改。"
        return {"system_prompt": system_prompt, "user_text": user_text}

    best_title = title
    for attempt in range(1, max_attempts + 1):

        print(f"第 {attempt} 次修改中……")
        title_length = len(best_title)
        if title_length > max_length:
            max_length -= 5  # 每次尝试减少最大长度限制

        return_message, _ = dispatcher.execute_with_group(
            build_message_info(best_title, title_length), group_name, format_json=True
        )
        best_title = extract_field(return_message, "title")

        if check_title(best_title, max_length, min_length, min_word):  # type: ignore
            return best_title  # type: ignore

    print("程序性缩减标题……")
    return shorten_title(best_title, max_length)
