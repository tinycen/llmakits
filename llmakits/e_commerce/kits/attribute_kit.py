from typing import Callable, Any, Tuple
from llmakits.dispatcher import ModelDispatcher
from llmakits.message import extract_field
from ..validators.value_validator import auto_validate


def _create_validate_func(choices: list) -> Callable[[str], Tuple[bool, Any]]:
    """
    创建验证函数的通用逻辑，使用auto_validate自动选择验证器
    当choices为空时，直接提取values并返回

    Args:
        choices: 可选项列表，为空时直接返回values

    Returns:
        验证函数
    """

    def validate_func(return_message: str) -> Tuple[bool, Any]:
        """
        验证函数：验证返回值是否符合要求

        Args:
            return_message: 返回的消息

        Returns:
            (验证是否通过, 验证通过的值)
        """
        values = extract_field(return_message, "values")

        # 如果没有choices，直接返回values
        if not choices:
            return True, values

        # values 必须是列表，且不能为空
        if not values or not isinstance(values, list):
            return False, None

        # 有choices时进行验证
        validated_values = []
        for value in values:
            validated_value = auto_validate(choices, value)
            if validated_value:
                validated_values.append(validated_value)

        if len(validated_values) < 1:
            return False, None

        return True, validated_values

    return validate_func


def fill_attr(dispatcher: ModelDispatcher, message_info: dict, group: str, choices: list):
    """
    填充属性值

    Args:
        dispatcher: 模型调度器
        message_info: 消息信息
        group: 组名
        choices: 可选项列表

    Returns:
        执行结果
    """
    validate_func = _create_validate_func(choices)
    result, _ = dispatcher.execute_with_group(message_info, group, format_json=True, validate_func=validate_func)  # type: ignore
    return result
