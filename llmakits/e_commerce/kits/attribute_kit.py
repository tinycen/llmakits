from typing import Optional, Callable, Any, Tuple
from llmakits.dispatcher import ModelDispatcher
from llmakits.message import extract_field
from ..validators.value_validator import validate_dict, validate_string


def fill_attr(dispatcher: ModelDispatcher, message_info: dict, group: str, choices: list):
    if choices:
        # 判断 choices 第1个值是 字典 还是 字符串
        if isinstance(choices[0], dict):

            def validate_dict_func(return_message) -> Tuple[bool, Any]:
                """
                说明：validate_func 作为闭包引用了外部的 options 变量，
                即使 send_message 只传递 return_message 参数，这里依然可以访问 options。
                返回：(验证是否通过, 验证通过的值)
                """
                values = extract_field(return_message, "values")
                validated_values = []
                for value in values:
                    validated_value = validate_dict(choices, value)
                    if not validated_value:
                        return False, None
                    validated_values.append(validated_value)
                return True, validated_values
            
            validate_func = validate_dict_func

        else:
            # 字符串 类型
            def validate_string_func(return_message) -> Tuple[bool, Any]:
                """
                说明：validate_func 作为闭包引用了外部的 options 变量，
                即使 send_message 只传递 return_message 参数，这里依然可以访问 options。
                返回：(验证是否通过, 验证通过的值)
                """
                values = extract_field(return_message, "value")
                validated_values = []
                for value in values:
                    validated_value = validate_string(choices, value)
                    if not validated_value:
                        return False, None
                    validated_values.append(validated_value)
                return True, validated_values
            
            validate_func = validate_string_func

    else:
        validate_func: Optional[Callable[[str], Tuple[bool, Any]]] = None

    result, _ = dispatcher.execute_with_group(message_info, group, format_json=True, validate_func=validate_func)
    return result
