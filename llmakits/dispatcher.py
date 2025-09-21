"""
模型调度器
负责多模型故障转移和负载均衡
"""

from typing import List, Dict, Any, Optional, Callable
from llmakits.message import convert_to_json
from llmakits.load_model import load_models


class ModelDispatcher:
    """
    模型调度器类，负责管理模型切换次数和执行任务
    """

    def __init__(self, models_config_path: Optional[str] = None, model_keys_path: Optional[str] = None):
        self.model_switch_count = 0
        if models_config_path and model_keys_path:
            self.model_groups, self.model_keys = load_models(models_config_path, model_keys_path)
        else:
            self.model_groups = {}
            self.model_keys = {}

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

    def execute_task(
        self,
        message_info: Dict[str, Any],
        llm_models: List[Dict[str, Any]],
        format_json: bool = False,
        validate_func: Optional[Callable[[str], bool]] = None,
    ) -> tuple[Any, int]:
        """
        执行任务 - 多模型调度器支持故障转移和重试

        Args:
            message_info:
                { "system_prompt": "", "user_text": "", "include_img": False, "img_list": [] }
            llm_models: LLM模型列表，每个元素包含model、sdk_name等
            format_json: 是否格式化为JSON
            validate_func: 结果验证函数

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
                    # 如果validate_func返回的是元组，解包处理
                    if is_valid:
                        if validated_value:
                            # 验证通过，直接返回验证通过的值
                            return validated_value, total_tokens
                    else:
                        print(base_model_info)
                        print("输出结果：条件校验失败, trying next model ...")
                        self.model_switch_count += 1
                        continue

                return return_message, total_tokens

            except Exception as e:
                print(base_model_info)

                # 检查是否是API密钥用尽异常
                if str(e) == 'API_KEY_EXHAUSTED':
                    print(f"模型 {sdk_name} - {model_name} API密钥 已用完")
                    # 从模型组中删除该模型
                    self._remove_exhausted_model(sdk_name, model_name)

                if idx < models_num - 1:
                    print("model failed, trying next model ...")
                    self.model_switch_count += 1
                    continue
                else:
                    raise e

        # 如果所有模型都失败
        raise Exception("All models failed.")

    def execute_with_group(
        self,
        message_info: Dict[str, Any],
        group_name: str,
        format_json: bool = False,
        validate_func: Optional[Callable[[str], bool]] = None,
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
