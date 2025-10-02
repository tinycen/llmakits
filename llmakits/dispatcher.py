"""
模型调度器
负责多模型故障转移和负载均衡
"""

from typing import List, Dict, Any, Optional, Callable, Union
from funcguard.printer import print_line, print_block
from .message import convert_to_json
from .load_model import load_models


class ModelDispatcher:
    """
    模型调度器类，负责管理模型切换次数和执行任务
    """

    def __init__(
        self,
        models_config: Optional[Union[str, Dict[str, Any]]] = None,
        model_keys: Optional[Union[str, Dict[str, Any]]] = None,
    ):
        self.model_switch_count = 0
        self.exhausted_models = []

        if models_config and model_keys:
            self.model_groups, self.model_keys = load_models(models_config, model_keys)
        else:
            self.model_groups = {}
            self.model_keys = {}

    # 输出报告
    def report(self):
        print(f"Model switch count: {self.model_switch_count}")
        if self.exhausted_models:
            print(f"Exhausted models: {self.exhausted_models}")
        return

    # 移除Token已用尽的模型
    def _remove_exhausted_model(self, sdk_name: str, model_name: str):
        """
        从模型组中删除API密钥用尽的模型

        Args:
            sdk_name: 模型的SDK名称
            model_name: 模型的名称
        """
        # 从当前列表中删除匹配的模型
        for group_name, group_models in self.model_groups.items():
            new_group_models = []
            for model in group_models:
                if model['sdk_name'] != sdk_name or model['model_name'] != model_name:
                    new_group_models.append(model)
            self.model_groups[group_name] = new_group_models
        return

    def _print_next_model_info(self, llm_models: List[Dict[str, Any]], current_idx: int, models_num: int):
        """
        打印下一个模型的信息

        Args:
            llm_models: LLM模型列表
            current_idx: 当前模型索引
            models_num: 模型总数
        """
        if current_idx < models_num - 1:
            next_model_info = llm_models[current_idx + 1]
            next_sdk_name = next_model_info.get('sdk_name', 'unknown_sdk')
            next_model_name = next_model_info.get('model_name', 'unknown_model')
            next_base_model_info = f"{current_idx+2}/{models_num} Model {next_sdk_name} : {next_model_name}"
            print_block("Next model", next_base_model_info, "> ", 20)

    # 执行任务 - 多模型调度器支持故障转移和重试
    def execute_task(
        self,
        message_info: Dict[str, Any],
        llm_models: List[Dict[str, Any]],
        format_json: bool = False,
        validate_func: Optional[Callable[[str], tuple[bool, Any]]] = None,
    ) -> tuple[Any, int]:
        """
        执行任务 - 多模型调度器支持故障转移和重试

        Args:
            message_info:
                { "system_prompt": "", "user_text": "", "include_img": False, "img_list": [] }
            llm_models: LLM模型列表，每个元素包含model、sdk_name等
            format_json: 是否格式化为JSON
            validate_func: 结果验证函数，可返回tuple[bool, Any]。
                        bool：True表示验证通过，False表示验证失败
                        Any：验证通过的值

        Returns:
            (返回消息, token总数)
        """
        models_num = len(llm_models)

        for idx, model_info in enumerate(llm_models):
            sdk_name = model_info.get('sdk_name', 'unknown_sdk')
            model_name = model_info.get('model_name', 'unknown_model')
            base_model_info = f"{idx+1}/{models_num} Model {sdk_name} : {model_name}"
            try:
                return_message, total_tokens = model_info["model"].send_message([], message_info)
                if format_json:
                    return_message = convert_to_json(return_message)

                # 如果有校验函数，校验不通过则继续下一个模型
                if validate_func is not None:
                    is_valid, validated_value = validate_func(return_message)

                    if is_valid:
                        if validated_value:
                            # 验证通过，直接返回验证通过的值
                            return validated_value, total_tokens
                    else:
                        content = "输出结果：条件校验失败, trying next model ..."
                        print_block(base_model_info, content)
                        self.model_switch_count += 1
                        # 打印下一个模型的信息
                        self._print_next_model_info(llm_models, idx, models_num)
                        continue

                return return_message, total_tokens

            except Exception as e:
                print_line("=")
                print(base_model_info)

                # 检查是否是API密钥用尽异常
                if str(e) == 'API_KEY_EXHAUSTED':
                    print(f"{sdk_name} - {model_name} API密钥 已用完")
                    # 从模型组中删除该模型
                    self._remove_exhausted_model(sdk_name, model_name)
                    self.exhausted_models.append(f"{sdk_name}_{model_name}")
                else:
                    # 打印详细的错误信息
                    print(f"错误详情: {e}")

                if idx < models_num - 1:
                    print("model failed, trying next model ...")
                    # 打印下一个模型的信息
                    self._print_next_model_info(llm_models, idx, models_num)
                    print_line("=")
                    self.model_switch_count += 1
                    continue
                else:
                    raise e

        # 如果所有模型都失败
        raise Exception("All models failed.")

    # 执行任务 - 模型组调度器
    def execute_with_group(
        self,
        message_info: Dict[str, Any],
        group_name: str,
        format_json: bool = False,
        validate_func: Optional[Callable[[str], tuple[bool, Any]]] = None,
    ) -> tuple[Any, int]:
        """
        使用内部model_groups执行任务，避免重复实例化导致的状态丢失

        这是推荐的使用方式，因为：
        1. 模型实例在dispatcher中缓存，避免重复实例化
        2. 模型内部的API密钥切换状态会保持（同一个对象引用）
        3. 多次调用不会丢失已切换的密钥状态

        Args:
            message_info:
                { "system_prompt": "", "user_text": "", "include_img": False, "img_list": [] }
            group_name: 模型组名称
            format_json: 是否格式化为JSON
            validate_func: 结果验证函数

        Returns:
            (返回消息, token总数)
        """
        if not self.model_groups:
            raise Exception("没有可用的模型组，请先初始化dispatcher")

        # 获取模型列表（这些是缓存的模型实例，保持API密钥切换状态）
        llm_models = self.model_groups[group_name]
        if not llm_models:
            raise Exception(f"未找到模型组: {group_name}")

        # 使用现有的execute_task方法，传入group_name以便在API密钥用尽时删除模型
        return self.execute_task(message_info, llm_models, format_json, validate_func)
