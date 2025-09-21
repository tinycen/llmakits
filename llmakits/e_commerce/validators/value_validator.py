from typing import Any, Dict, List, Union, Callable


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


def auto_validate(item_list: List[Any], search_data: Any) -> Union[Dict[str, Any], str, None]:
    """
    根据item_list的第一个元素类型自动选择验证程序

    Args:
        item_list: 要搜索的列表，可以是字典列表或字符串列表
        search_data: 要查找的数据，字典或字符串

    Returns:
        匹配到的值：字典验证返回Dict，字符串验证返回str，未找到返回None
    """
    if not item_list:
        print("item_list 为空列表")
        return None

    # 根据列表第一个元素的类型选择验证器
    first_item = item_list[0]

    if isinstance(first_item, dict):
        # 字典类型验证
        if not isinstance(search_data, dict):
            print(f"字典类型验证需要search_data为字典，实际类型: {type(search_data)}")
            return None
        return validate_dict(item_list, search_data)

    elif isinstance(first_item, str):
        # 字符串类型验证
        if not isinstance(search_data, str):
            print(f"字符串类型验证需要search_data为字符串，实际类型: {type(search_data)}")
            return None
        return validate_string(item_list, search_data)

    else:
        print(f"不支持的列表元素类型: {type(first_item)}")
        return None
