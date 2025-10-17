"""
类目验证功能
"""

from typing import Any, Callable, Dict, List, Tuple

from ...validators.value_validator import validate_dict
from .utils import standardize_category_format


def create_category_validate_func(category_all: List[Dict[str, Any]]) -> Callable[[str], Tuple[bool, Any]]:
    """
    创建类目验证函数，用于全部类目一起预测的场景

    Args:
        category_all: 所有可选类目列表

    Returns:
        验证函数
    """

    def validate_func(return_message: str) -> Tuple[bool, Any]:
        """
        验证函数：验证返回的类目是否在可选范围内

        Args:
            return_message: LLM返回的消息

        Returns:
            (验证是否通过, 验证通过的值列表)
        """

        if not return_message:
            return False, None

        # 标准化格式
        standardized_message = standardize_category_format(return_message)  # pyright: ignore[reportArgumentType]

        # 验证每个类目
        predict_results = []
        for category in standardized_message:
            if isinstance(category, dict):
                search_data = {"cat_id": category.get("cat_id", ""), "cat_name": category.get("cat_name", "")}
                value = validate_dict(category_all, search_data)
                if value:
                    predict_results.append(value)

        # 所有类目都验证通过
        if predict_results:
            return True, predict_results
        else:
            # 如果标准化后的消息不为空，但没有验证通过的类目，则验证失败
            if standardized_message:
                print("警告: 预测结果中，没有任何一个验证通过，以下是标准化后的预测结果（standardized_message）: ")
                print(standardized_message)
            return False, predict_results

    return validate_func
