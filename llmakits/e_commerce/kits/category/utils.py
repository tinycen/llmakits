"""
类目处理工具函数
"""

from typing import Any, Dict, List, Optional
from ....dispatcher import ModelDispatcher
from ....dispatcher_control import execute_with_repair


def standardize_category_format(cat_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化类目数据格式，统一使用cat_id和cat_name键名"""
    if not cat_data:
        return []

    first_item = cat_data[0]
    if isinstance(first_item, dict):
        if 'value' in first_item and 'label' in first_item:
            return [{'cat_id': item['value'], 'cat_name': item['label']} for item in cat_data]
        elif 'cat_id' in first_item and 'cat_name' in first_item:
            return cat_data

    return cat_data


def extr_cat_tree(cat_tree, level=1, level_1_names=None, level_2_names=None):
    """根据指定的 level 参数提取对应的层级信息"""
    cat_tree = [node for node in cat_tree if node["label"] != "最近添加"]
    result = []

    if level_1_names is not None:
        level_1_names = [cat["cat_name"] for cat in level_1_names]

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

        if level_1_names is None and level_2_names is not None:
            level_1_names = list(level_2_filters.keys())

    if level == 1:
        unique_values = list({node['value'] for node in cat_tree})
        result = [{'cat_id': value, 'cat_name': value} for value in unique_values]

    elif level == 2:
        for level_1_node in cat_tree:
            if level_1_names is None or level_1_node['value'] in level_1_names:
                children = level_1_node.get('children', [])
                if children:
                    for level_2_node in children:
                        cat_id = f"{level_1_node['value']} > {level_2_node['value']}"
                        cat_name = f"{level_1_node['label']} > {level_2_node['label']}"
                        result_item = {'cat_id': cat_id, 'cat_name': cat_name}
                        if result_item not in result:
                            result.append(result_item)

    elif level == 3:
        for level_1_node in cat_tree:
            if level_1_names is None or level_1_node['value'] in level_2_filters:
                for level_2_node in level_1_node.get('children', []):
                    should_include = level_2_names is None or (
                        level_1_node['value'] in level_2_filters
                        and level_2_node['value'] in level_2_filters[level_1_node['value']]
                    )

                    if should_include:
                        level_3_children = level_2_node.get('children', [])
                        if level_3_children:
                            for level_3_node in level_3_children:
                                level_label_3 = level_3_node['label']
                                cat_id_path = (
                                    f"{level_1_node['value']} > {level_2_node['value']} > {level_3_node['value']}"
                                )
                                cat_name_path = f"{level_1_node['label']} > {level_2_node['label']} > {level_label_3}"
                                result.append({'cat_id': cat_id_path, 'cat_name': cat_name_path})

    return result


def get_category_depth(cat_tree: Any) -> int:
    """检测类目树的最大深度"""
    max_depth = 1

    for level_1_node in cat_tree:
        level_2_children = level_1_node.get('children', [])
        if level_2_children:
            max_depth = max(max_depth, 2)
            for level_2_node in level_2_children:
                level_3_children = level_2_node.get('children', [])
                if level_3_children:
                    max_depth = max(max_depth, 3)
                    break
            if max_depth == 3:
                break

    return max_depth


def prepare_category_data(cat_tree: Any, max_depth: int = 3) -> Any:
    """准备类目数据，根据深度标准化或提取"""
    target_depth = min(get_category_depth(cat_tree), max_depth)

    if target_depth == 1:
        return standardize_category_format(cat_tree)
    else:
        return extr_cat_tree(cat_tree, level=target_depth)


def create_message_info(
    title: str, category_all: Any, system_prompt: str, image_url: str = ""
) -> tuple[Dict[str, Any], str]:
    """创建消息信息和用户文本"""
    user_text = f"商品标题:{title},可选类目:{category_all}"

    message_info = {
        "user_text": user_text,
        "system_prompt": system_prompt,
        "include_img": bool(image_url),
        "img_list": [image_url] if image_url else [],
    }

    return message_info, user_text


def execute_prediction(
    dispatcher: ModelDispatcher,
    message_info: Dict[str, Any],
    group_name: str,
    validate_func: Optional[Any] = None,
    fix_json_config: dict = {},
) -> List[Dict[str, Any]]:
    """执行预测并返回结果"""
    predict_results, _ = execute_with_repair(
        dispatcher,
        message_info,
        group_name,
        validate_func=validate_func,
        fix_json_config=fix_json_config,
    )
    return predict_results
