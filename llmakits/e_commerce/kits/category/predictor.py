"""
类目预测核心功能
"""

from typing import Any, Dict, List, Optional, Union
from ....dispatcher import ModelDispatcher
from ...validators.value_validator import validate_dict
from .utils import (
    standardize_category_format,
    extr_cat_tree,
    get_category_depth,
    prepare_category_data,
    create_message_info,
    execute_prediction,
    match_recall_merge,
)
from .validator import create_category_validate_func


def predict_cat_direct(
    dispatcher: ModelDispatcher,
    product: dict,
    cat_tree: Any,
    predict_config: dict,
    fix_json_config: dict = {},
) -> List[Dict[str, Any]]:
    """
    直接预测商品类目（全部类目一起预测，带验证器）

    适用场景：类目数量较少，或希望一次性预测所有层级

    Args:
        dispatcher: 模型调度器
        product: 商品信息字典，包含 "title" 和 "image_url"
        cat_tree: 类目树数据
        predict_config:
            {
                system_prompt: 系统提示词,
                use_rag: 是否使用RAG（可选，默认False）,
                user_suggest_cats: [{"cat_id": "……", "cat_name": "……"}]  # 可选：用户建议类目范围
            }
        fix_json_config:
            {
                "group_name": "fix_json",  # 修复模型组名称
                "system_prompt": "你是JSON修复专家...",
                "example_json": '{"key": "value"}'  # 可选：JSON示例
            }

    Returns:
        预测的类目结果列表
    """
    # 准备商品信息
    title = product.get("title", "")
    image_url = product.get("image_url", "")

    # 准备类目数据
    category_all = prepare_category_data(cat_tree)
    use_rag = predict_config.get("use_rag", False)
    user_suggest_cats = predict_config.get("user_suggest_cats", [])

    if use_rag:
        category_all = user_suggest_cats
        # matched_results = match_recall(category_all, title)
        # category_all = match_recall_merge(matched_results, user_suggest_cats)
        # if not category_all:
        #     raise ValueError("RAG匹配结果为空，且用户建议类目也为空，无法进行预测")

    # 创建验证函数
    validate_func = create_category_validate_func(category_all)

    # 准备消息信息
    predict_system_prompt = predict_config["system_prompt"]
    message_info, _ = create_message_info(title, category_all, predict_system_prompt, image_url)

    # 执行预测
    try:
        group_name = "with_image" if image_url else "without_image"
        return execute_prediction(dispatcher, message_info, group_name, validate_func, fix_json_config)
    except Exception:
        if image_url:
            print("预测失败，尝试去掉图片后预测……")
            message_info["include_img"] = False
            message_info["img_list"] = []
            return execute_prediction(dispatcher, message_info, "without_image", validate_func, fix_json_config)
        return []


def predict_cat_gradual(
    dispatcher: ModelDispatcher,
    product: dict,
    cat_tree: Any,
    predict_config: dict,
    fix_json_config: dict = {},
) -> List[Dict[str, Any]]:
    """
    梯度预测商品类目（逐级预测，无验证器）

    适用场景：类目数量较多，需要逐级缩小范围

    注意：此方法不使用验证器，因为每一级的验证目标都在变化
    如需验证，建议在每一级预测后手动检查结果

    Args:
        dispatcher: 模型调度器
        product: 商品信息字典
        cat_tree: 类目树数据
        predict_config: { system_prompt: 系统提示语, group_name: 模型组名称 }
        fix_json_config: JSON修复配置（可选）

    Returns:
        预测的类目结果列表
    """
    max_depth = get_category_depth(cat_tree)
    target_depth = min(max_depth, 3)

    if target_depth == 1:
        category_all = standardize_category_format(cat_tree)
    else:
        category_all = extr_cat_tree(cat_tree, level=target_depth)

    return_message: Union[str, List[str], Dict[str, Any]] = ""
    level_1_names: Optional[Union[List[str], str]] = None
    level_2_names: Optional[Union[List[str], str]] = None

    title = product.get("title", "")
    image_url = product.get("image_url", "")

    if image_url:
        include_img = True
        img_list = [image_url]
    else:
        include_img = False
        img_list = []

    # 逐级预测
    for level in range(1, target_depth + 1):
        if target_depth > 1:
            category_options = extr_cat_tree(
                cat_tree, level=level, level_1_names=level_1_names, level_2_names=level_2_names
            )
        else:
            category_options = category_all

        user_text = f"商品标题:{title},可选类目:{category_options}"
        message_info = {
            "user_text": user_text,
            "system_prompt": predict_config["system_prompt"],
            "include_img": include_img,
            "img_list": img_list,
        }

        # 不使用验证器，因为每一级的验证目标都在变化
        return_message, _ = execute_prediction(
            dispatcher,
            message_info,
            predict_config["group_name"],
            fix_json_config=fix_json_config,
        )

        if not return_message:
            return []

        # 更新下一级的过滤条件
        if level == 1 and target_depth > 1:
            level_1_names = return_message if isinstance(return_message, (str, list)) else None
        elif level == 2:
            level_2_names = return_message if isinstance(return_message, (str, list)) else None

    # 最后一级的结果需要手动验证
    standardized_return_message = standardize_category_format(return_message)  # pyright: ignore[reportArgumentType]
    predict_results = []

    for category in standardized_return_message:
        if isinstance(category, dict):
            search_data = {"cat_id": category.get("cat_id", ""), "cat_name": category.get("cat_name", "")}
            value = validate_dict(category_all, search_data)
            if value:
                predict_results.append(value)

    return predict_results
