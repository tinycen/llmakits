from typing import Any, Dict, List, Union, Callable


def validate_dict(item_list: List[Dict[str, Any]], search_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并查找指定值是否存在于字典列表中

    :param item_list: (list[dict]): 要搜索的字典列表
    :param search_data: dict, 键名应与item_list中字典的键名一致
    :return: dict, 匹配到的项，包含与search_data相同的键
    """
    if not isinstance(item_list, list) or not all(isinstance(item, dict) for item in item_list):
        raise TypeError("item_list 必须是字典组成的列表")

    if not item_list:
        print("item_list 为空列表")
        return {}

    # 获取item_list中第一个字典的键名
    first_item_keys = set(item_list[0].keys())
    search_data_keys = set(search_data.keys())

    # 检查search_data的键是否与item_list中字典的键一致
    if not search_data_keys.issubset(first_item_keys):
        raise ValueError(f"search_data的键 {search_data_keys} 必须是item_list中字典键 {first_item_keys} 的子集")

    # 获取search_data的键和值
    search_keys = list(search_data.keys())
    search_values = [search_data[key] for key in search_keys]

    # 在item_list中查找匹配项
    for item in item_list:
        # 检查所有search_data的键值是否都匹配
        if all(item.get(key) == value for key, value in zip(search_keys, search_values)):
            # 返回包含相同键的结果
            return {key: item.get(key) for key in search_keys}

    # 未找到匹配项
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
