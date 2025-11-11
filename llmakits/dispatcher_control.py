"""
增强版 调度 策略

遇到非 JSON 错误，dispatcher 内部会自动尝试所有模型。
-----------------------------------------------
增强版：return_detailed=True 模式下：
JSON 错误 → 尝试修复 → 修复失败 → 继续下一个模型
非 JSON 错误 → 说明所有模型都已经在 dispatcher 内部尝试过了 → 直接抛出异常
-----------------------------------------------
传统：return_detailed=False 模式下：
JSON 错误 → 继续下一个模型
非 JSON 错误 → 同 return_detailed=True
"""

from typing import Dict, Any
from .dispatcher import ModelDispatcher
from typing import Dict, Any, Optional, Callable
from funcguard import print_line, print_block


def _get_model_info(dispatcher: ModelDispatcher, group_name: str, index: int) -> tuple[str, str, int]:
    """
    获取指定索引的模型信息

    Args:
        dispatcher: 模型调度器
        group_name: 模型组名称
        index: 模型索引

    Returns:
        (sdk名称, 模型名称, 模型总数)
    """
    llm_models = dispatcher.model_groups.get(group_name, [])
    models_num = len(llm_models)

    if index < models_num:
        model_info = llm_models[index]
        sdk_name = model_info.get('sdk_name', 'unknown_sdk')
        model_name = model_info.get('model_name', 'unknown_model')
        return sdk_name, model_name, models_num
    return 'unknown_sdk', 'unknown_model', models_num


def _print_next_model_info(dispatcher: ModelDispatcher, group_name: str, current_idx: int) -> None:
    """
    打印下一个模型的信息

    Args:
        dispatcher: 模型调度器
        group_name: 模型组名称
        current_idx: 当前模型索引
    """
    next_sdk_name, next_model_name, models_num = _get_model_info(dispatcher, group_name, current_idx + 1)

    if current_idx + 1 < models_num:
        next_base_model_info = f"Next model : \n{current_idx+2}/{models_num} Model {next_sdk_name} : {next_model_name}"
        print_line(".")
        print(next_base_model_info)
    else:
        print("Next model does not exist.")


def _print_current_model_info(dispatcher: ModelDispatcher, group_name: str, current_idx: int) -> str:
    """
    获取当前模型信息字符串

    Args:
        dispatcher: 模型调度器
        group_name: 模型组名称
        current_idx: 当前模型索引

    Returns:
        当前模型信息字符串
    """
    sdk_name, model_name, models_num = _get_model_info(dispatcher, group_name, current_idx)
    return f"{current_idx+1}/{models_num} Model {sdk_name} : {model_name}"


def dispatcher_with_repair(
    dispatcher: ModelDispatcher,
    message_info: Dict[str, Any],
    group_name: str,
    validate_func: Optional[Callable[[str], tuple[bool, Any]]] = None,
    fix_json_config: Dict[str, Any] = {},
) -> tuple[Any, int]:
    """
    任务执行与修复策略

    特点：
    1. 为每个失败的模型都尝试修复（限制总次数）
    2. 处理所有类型的错误（JSON、网络、API密钥等）
    3. 确保所有主模型都有机会尝试
    4. 独立的修复调度器，避免状态混乱

    Args:
        dispatcher: 主模型调度器
        message_info: 消息信息
        group_name: 主模型组名称
        validate_func: 可选的验证函数
        fix_json_config: 修复配置
            {
                "group_name": "fix_json",  # 修复模型组名称
                "system_prompt": "你是JSON修复专家...",
                "example_json": '{"key": "value"}'  # 可选：JSON示例
            }

    Returns:
        (返回消息, token总数)

    Raises:
        Exception: 所有模型和修复尝试均失败
    """
    if not dispatcher.model_groups.get(group_name):
        raise ValueError(f"主调度器中未找到模型组: {group_name}")

    if fix_json_config:
        if not dispatcher.model_groups.get(fix_json_config["group_name"]):
            raise ValueError(f"调度器中未找到 修复模型组: {fix_json_config['group_name']}")

    current_index = 0

    while True:
        # 每次循环都重新获取模型总数，因为模型可能被删除
        total_models_main = len(dispatcher.model_groups[group_name])

        # 如果没有可用的模型了，退出循环
        if total_models_main == 0 or current_index >= total_models_main:
            break

        # 执行主模型
        result = dispatcher.execute_with_group(
            message_info,
            group_name,
            format_json=True,
            validate_func=validate_func,
            start_index=current_index,
            return_detailed=True,
        )

        # 成功！
        if result.success:
            return result.return_message, result.total_tokens

        error_message = str(result.error)
        # 失败处理，尝试修复（仅限 JSON 错误且有原始消息）
        if result.return_message and fix_json_config and "json_error" in error_message:
            print("尝试修复JSON……")
            # 构造修复消息
            user_text = f"以下是一个格式错误的JSON字符串，请修复它：\n\n{result.return_message}"

            if "example_json" in fix_json_config:
                user_text += f"\n\n期望的JSON格式示例：\n{fix_json_config['example_json']}"

            if "system_prompt" in fix_json_config:
                fix_json_system_prompt = fix_json_config["system_prompt"]
            else:
                fix_json_system_prompt = '''
                    # 角色
                    你是一个JSON编程专家，能够仔细分析用户提供的错误JSON代码，并按照正确示范进行修复。并以JSON格式输出修复后的内容。

                    ## 技能
                    ### 技能 1: JSON修复
                    1. 仔细检查用户提供的错误JSON代码，并参考用户提供的正确示范，进行修复。

                    ## 限制
                    - 输出必须严格遵循指定示范的JSON格式，字段key命名确保与示范完全一致。
                    - 确保输出的JSON格式符合规范，禁止输出错误的JSON格式。
                    - 仅输出修正后的JSON代码，请勿输出任何额外的内容。
                '''

            repair_message_info = {"user_text": user_text, "system_prompt": fix_json_system_prompt}
            try:
                # 开始执行修复
                fixed_message, repair_tokens = dispatcher.execute_with_group(  # type: ignore
                    repair_message_info,
                    fix_json_config["group_name"],
                    format_json=True,
                    return_detailed=False,  # 修复器用简单模式
                )

                # 检查修复后的结果
                print("修复后的JSON ：")
                print(fixed_message)

                # 重要：修复后的结果需要再次验证，确保符合要求
                if validate_func:
                    is_valid, validated_result = validate_func(fixed_message)
                    if is_valid:
                        return validated_result, repair_tokens
                    else:
                        current_model_info = _print_current_model_info(dispatcher, group_name, current_index)
                        print_line("=")
                        print(current_model_info)
                        content = "修复后的JSON未通过验证, trying next model..."
                        print_block(current_model_info, content)
                        _print_next_model_info(dispatcher, group_name, current_index)
                        print_line("=")
                        # 验证失败，继续尝试下一个模型
                        current_index = result.last_tried_index + 1
                        continue
                else:
                    # 如果没有验证函数，直接返回修复结果
                    return fixed_message, repair_tokens
            except Exception as e:
                current_model_info = _print_current_model_info(dispatcher, group_name, current_index)
                print_line("=")
                print(current_model_info)
                print(f"修复JSON失败: {e}")
                _print_next_model_info(dispatcher, group_name, current_index)
                print_line("=")
                # 修复失败，自动 移动到下一个模型
                current_index = result.last_tried_index + 1
                continue

        elif "All models failed" not in error_message:
            current_model_info = _print_current_model_info(dispatcher, group_name, current_index)
            print_line("=")
            print(current_model_info)
            print("model failed, trying next model ...")
            _print_next_model_info(dispatcher, group_name, current_index)
            print_line("=")
            current_index = result.last_tried_index + 1

        else:
            raise result.error  # type: ignore

    raise Exception(f"所有模型均尝试失败")
