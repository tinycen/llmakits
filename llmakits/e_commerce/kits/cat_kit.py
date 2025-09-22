from typing import Any, Dict, List, Optional, Union
from ..validators.value_validator import validate_dict
from ...dispatcher import ModelDispatcher


# 提取类目树
def extr_cat_tree(cat_tree, level=1, level_1_names=None, level_2_names=None):
    """
    根据指定的 level 参数提取对应的层级信息，根据不同层级进行过滤：
    - level 1: 不进行任何过滤
    - level 2: 只按 level_1_names 过滤
    - level 3: 同时按 level_1_names 和 level_2_names 过滤

    :param cat_tree: 类目树数据，格式为 list[dict]
    :param level: 提取的层级，可选值为 1, 2, 3
    :param level_1_names: 可选，用于在 level 2 和 3 时过滤特定的 level_1 类目，格式为列表
        示例值： [{"cat_name": "儿童用品"}, {"cat_name": "美容和卫生"}, {"cat_name": "日化"}]
    :param level_2_names: 可选，用于在 level 3 时过滤特定的 level_2 类目，格式为包含 "level_1 > level_2" 的列表
        示例值：[{"cat_name": "美容和卫生 > 护理化妆品"}, {"cat_name": "儿童用品 > 产妇和新生儿用品"}]
    :return: 提取后的层级信息列表
    """
    # 从 cat_tree 中移除 "最近添加" 的一级类目，并返回剩余的节点
    cat_tree = [node for node in cat_tree if node["label"] != "最近添加"]

    if level_1_names == level_2_names is None:
        cat_keys = ["value", "label"]
    else:
        cat_keys = ["cat_id", "cat_name"]

    result = []

    if level_1_names is not None:
        level_1_names = [cat["cat_name"] for cat in level_1_names]

    # 处理 level_2_names，解析出实际的 level_1 和 level_2 名称对
    level_2_filters = {}
    if level == 3 and level_2_names:
        level_2_names = [cat["cat_name"] for cat in level_2_names]
        for level_2_path in level_2_names:
            parts = level_2_path.split(" > ")
            if len(parts) == 2:
                level_1_name = parts[0]
                level_2_name = parts[1]
                if level_1_name not in level_2_filters:
                    level_2_filters[level_1_name] = set()
                level_2_filters[level_1_name].add(level_2_name)

        # 检查并重置level_1_names
        if level_1_names is None and level_2_names is not None:
            level_1_names = list(level_2_filters.keys())

    if level == 1:
        # level 1 不进行任何过滤，直接返回所有 level_1
        result = list({node['value'] for node in cat_tree})

    elif level == 2:
        for level_1_node in cat_tree:
            if level_1_names is None or level_1_node['value'] in level_1_names:
                for level_2_node in level_1_node.get('children', []):
                    val = f"{level_1_node[ 'value' ]} > {level_2_node[ 'value' ]}"
                    if val not in result:
                        result.append(val)

    elif level == 3:

        for level_1_node in cat_tree:
            # 检查 level_1 是否匹配
            if level_1_names is None or level_1_node['value'] in level_2_filters:
                for level_2_node in level_1_node.get('children', []):
                    # 检查 level_2 是否匹配
                    should_include = level_2_names is None or (
                        level_2_node['value'] in level_2_filters[level_1_node['value']]
                    )

                    if should_include:
                        for level_3_node in level_2_node.get('children', []):
                            level_label_3 = level_3_node['label']
                            val = f"{level_1_node[ 'value' ]} > {level_2_node[ 'value' ]} > {level_label_3}"
                            result.append({cat_keys[0]: level_3_node['value'], cat_keys[1]: val})

    return result


def predict_category(dispatcher: ModelDispatcher, title: str, cat_tree: Any, system_prompt: str, group_name: str):
    """预测商品类目

    通过三级预测流程，逐级预测商品的一级、二级、三级类目

    Args:
        dispatcher: 模型调度器
        title: 商品标题
        cat_tree: 类目树数据
        system_prompt: 系统提示语
        group_name: 模型组名称

    Returns:
        预测的类目结果列表，每个结果包含 value 和 label

    Raises:
        ValueError: 当未预测到类目时抛出

    Example:
        >>> predict_category(dispatcher, "护发喷雾", cat_tree, prompt, "group")
        [{'value': '17028992-93942', 'label': '美容和卫生 > 护发产品 > 护发喷雾'}]
    """
    category_all = extr_cat_tree(cat_tree, level=3)
    return_message: Union[str, List[str], Dict[str, Any]] = ""
    level_1_names: Optional[Union[List[str], str]] = None
    level_2_names: Optional[Union[List[str], str]] = None

    for level in [1, 2, 3]:
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

    if not return_message:
        raise ValueError("未预测到类目")

    predict_results = []
    for category in return_message:
        if isinstance(category, dict):
            search_data = {"value": category.get("cat_id", ""), "label": category.get("cat_name", "")}
            value = validate_dict(category_all, search_data)
            predict_results.append(value)

    return predict_results
