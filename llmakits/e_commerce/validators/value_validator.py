from typing import Any, Dict, List, Union


def validate_dict(choices: List[Dict[str, Any]], search_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并查找指定值是否存在于字典列表中

    :param choices: (list[dict]): 要搜索的字典列表
    :param search_data: dict, 键名应与choices中字典的键名一致
    :return: dict, 匹配到的项，包含与search_data相同的键
    """
    if not isinstance(choices, list) or not all(isinstance(item, dict) for item in choices):
        raise TypeError("choices 必须是字典组成的列表")

    if not choices:
        raise ValueError("choices 不能为空列表")

    # 获取choices中第一个字典的键名
    first_item_keys = set(choices[0].keys())
    search_data_keys = set(search_data.keys())

    # 检查search_data的键是否与choices中字典的键一致
    if not search_data_keys.issubset(first_item_keys):
        raise ValueError(f"search_data的键 {search_data_keys} 必须是choices中字典键 {first_item_keys} 的子集")

    # 对 search_data_keys 进行排序，包含了字符 "id" 或 "value" 的键放在前面（这样可以优先匹配）
    search_data_keys = sorted(search_data_keys, key=lambda x: (x.find("id") != -1, x.find("value") != -1))

    # 在choices中查找匹配项
    for item in choices:
        for search_data_key in search_data_keys:
            if item[search_data_key] == search_data[search_data_key]:
                return item

    # 未找到匹配项
    print(f"未找到匹配项: {search_data}")
    if len(choices) < 30:
        print(f"choices: {choices}")

    return {}


def validate_string(choices: List[str], search_value: str):
    """
    验证并查找指定字符串是否存在于字符串列表中

    :param choices: List[str], 要搜索的字符串列表
    :param search_value: str, 要查找的字符串值
    :return: str, 匹配到的字符串值
    """

    if search_value in choices:
        return search_value

    # 未找到匹配项
    print(f"未找到匹配项: {search_value}")
    if len(choices) < 30:
        print(f"choices: {choices}")
    return None


def auto_validate(choices: List[Any], search_data: Any) -> Union[Dict[str, Any], str, None]:
    """
    根据choices的第一个元素类型自动选择验证程序

    Args:
        choices: 要搜索的列表，可以是字典列表或字符串列表
        search_data: 要查找的数据，字典或字符串

    Returns:
        匹配到的值：字典验证返回Dict，字符串验证返回str，未找到返回None
    """
    if not choices:
        print("choices 为空列表")
        return None

    # 根据列表第一个元素的类型选择验证器
    first_item = choices[0]

    if isinstance(first_item, dict):
        # 字典类型验证
        if not isinstance(search_data, dict):
            print(f"字典类型验证需要search_data为字典，实际类型: {type(search_data)}")
            return None
        return validate_dict(choices, search_data)

    elif isinstance(first_item, str):
        # 字符串类型验证
        if not isinstance(search_data, str):
            print(f"字符串类型验证需要search_data为字符串，实际类型: {type(search_data)}")
            return None
        return validate_string(choices, search_data)

    else:
        print(f"不支持的列表元素类型: {type(first_item)}")
        return None
