from typing import Any, Dict, List


def validate_dict(item_list: List[Dict[str, Any]], search_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并查找指定值是否存在于字典列表中

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
    print(f"未找到匹配项: {search_data}")
    return {}


def validate_string(item_list: List[str], search_value: str):
    """
    验证并查找指定字符串是否存在于字符串列表中

    :param item_list: List[str], 要搜索的字符串列表
    :param search_value: str, 要查找的字符串值
    :return: str, 匹配到的字符串值
    """

    if search_value in item_list:
        return search_value

    # 未找到匹配项
    print(f"未找到匹配项: {search_value}")
    return None
