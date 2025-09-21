from typing import Any, Dict, List, Optional, Union
from .validators.string_validator import contains_chinese
from ..message import extract_field
from llmakits.dispatcher import ModelDispatcher


# 临时定义 extr_cat_tree 函数，避免导入错误
def extr_cat_tree(
    cat_tree: Any,
    level: int,
    level_1_names: Optional[Union[List[str], str]] = None,
    level_2_names: Optional[Union[List[str], str]] = None,
) -> List[Dict[str, str]]:
    """临时占位函数，需要替换为实际的 selectSql 模块实现"""
    return []


# 检查 输出的属性参数 是否存在
def find_value(item_list: List[Dict[str, Any]], search_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    :param item_list: (list[dict]): 要搜索的字典列表，每个字典应包含'id'和'value'键
    :param search_data: dict, 必须包含 'id' 和 'value' 两个键
    :return: dict, 匹配到的项，包含 'id' 和 'value'
    """
    if not isinstance(item_list, list) or not all(isinstance(item, dict) for item in item_list):
        raise TypeError("item_list 必须是字典组成的列表")

    if set(search_data.keys()) != {'id', 'value'}:
        raise ValueError("search_data 必须且只能包含 'id' 和 'value' 两个键")

    key_1 = 'id'
    key_2 = 'value'
    value_1 = search_data[key_1]
    value_2 = search_data[key_2]

    # 优先通过ID查找
    for item in item_list:
        if item.get(key_1) == value_1:
            return {key_1: item.get(key_1), key_2: item.get(key_2)}

    # ID查找失败后，尝试通过名称查找
    for item in item_list:
        if item.get(key_2) == value_2:
            return {key_1: item.get(key_1), key_2: item.get(key_2)}

    # 两种查找方式都未找到匹配项
    raise KeyError(f"未找到匹配项: {search_data}")


# 预测类目
def predict_category(dispatcher: ModelDispatcher, title: str, cat_tree: Any, system_prompt: str, group_name: str):
    category_all = extr_cat_tree(cat_tree, level=3)
    return_message: Union[str, List[str], Dict[str, Any]] = ""
    level_1_names: Optional[Union[List[str], str]] = None
    level_2_names: Optional[Union[List[str], str]] = None
    for level in [1, 2, 3]:
        # print(f"正在预测 {level} 级类目……")
        category_options = extr_cat_tree(
            cat_tree, level=level, level_1_names=level_1_names, level_2_names=level_2_names
        )
        user_text = f"商品标题:{title},可选类目:{category_options}"
        message_info = {"user_text": user_text, "system_prompt": system_prompt}
        return_message_raw, _ = dispatcher.execute_with_group(message_info, group_name, format_json=True)
        return_message = (
            return_message_raw if isinstance(return_message_raw, (str, dict, list)) else str(return_message_raw)
        )

        if level == 1:
            level_1_names = return_message if isinstance(return_message, (str, list)) else None
        elif level == 2:
            level_2_names = return_message if isinstance(return_message, (str, list)) else None

    # print( return_message )

    '''  示例响应结果
        [{'cat_name': '美容和卫生 > 护发产品 > 护发喷雾', 'cat_id': '17028992-93942'},
         {'cat_name': '美容和卫生 > 护发产品 > 头发精华素', 'cat_id': '17028992-93945'}]
    '''
    if not return_message:
        raise ValueError("未预测到类目")
    predict_results = []
    for category in return_message:
        if isinstance(category, dict):
            search_data = {"value": category.get("cat_id", ""), "label": category.get("cat_name", "")}
            value = find_value(category_all, search_data)
            predict_results.append(value)
    '''  示例响应结果
        [{'value': '17028992-93942', 'label': '美容和卫生 > 护发产品 > 护发喷雾'},
        {'value': '17028992-93945', 'label': '美容和卫生 > 护发产品 > 头发精华素'}]
    '''
    return predict_results


def translate_options(
    dispatcher: ModelDispatcher, title: str, options: List[str], to_lang: str, group_name: str, system_prompt: str
):
    """
    翻译选项，并确保输出列表长度与输入一致。

    :param title: 商品标题
    :param options: 原始选项列表
    :param to_lang: 目标语言
    :param group_name: 模型组名称
    :param system_prompt: 系统提示语
    :return: 翻译后的选项列表
    """
    # 首先检测源语言是否包含中文，如果不包含中文，就直接返回原语言
    if not contains_chinese(str(options)):
        return options, 0

    user_text = f"title:{title},options:{options},请翻译为:{to_lang}语言"

    # 验证条件：校验返回的 options 长度是否与原 options 一致
    def validate_func(return_message):
        """
        说明：validate_func 作为闭包引用了外部的 options 变量，
        即使 send_message 只传递 return_message 参数，这里依然可以访问 options。
        """
        translated_options = extract_field(return_message, "options")
        # 只有长度相等，且不存在重复值，才算验证通过
        if len(options) == len(translated_options) == len(set(translated_options)):
            return True
        else:
            return False

    return_message, _ = dispatcher.execute_with_group(
        {"user_text": user_text, "system_prompt": system_prompt},
        group_name,
        format_json=True,
        validate_func=validate_func,
    )
    extracted_options = extract_field(return_message, "options")
    return extracted_options
