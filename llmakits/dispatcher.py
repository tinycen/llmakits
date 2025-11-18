"""
模型调度器 - 支持索引控制和详细状态返回
"""

from typing import List, Dict, Any, Optional, Callable, Union, NamedTuple
from funcguard import print_line, print_block, time_monitor
from filekits.base_io import save_json
from .message import convert_to_json
from .load_model import load_models
from .utils.image_cache import ImageBase64Cache


class ExecutionResult(NamedTuple):
    """执行结果包装类"""

    return_message: Any = None  # 返回的消息内容
    total_tokens: int = 0  # 使用的token总数
    last_tried_index: int = -1  # 最后尝试的模型索引
    success: bool = False  # 是否成功
    error: Optional[Exception] = None  # 错误信息（失败时保留）


class ModelDispatcher:
    """
    模型调度器类，负责管理模型切换次数和执行任务
    """

    # 类级别的全局缓存，所有实例共享
    _global_image_cache = ImageBase64Cache(max_size=10)

    def __init__(
        self,
        models_config: Optional[Union[str, Dict[str, Any]]] = None,
        model_keys: Optional[Union[str, Dict[str, Any]]] = None,
        global_config: Optional[Union[str, Dict[str, Any]]] = None,
    ):
        self.model_switch_count = 0
        self.exhausted_models = []
        self.warning_time = None  # 用于 显示超时警告的阈值，单位秒

        if models_config and model_keys:
            self.model_groups, self.model_keys = load_models(models_config, model_keys, global_config)
            self.model_group_names = list(self.model_groups.keys())  # 新增：模型组名称列表
        else:
            self.model_groups = {}
            self.model_keys = {}
            self.model_group_names = []  # 新增：模型组名称列表

    @classmethod
    def get_image_cache(cls) -> ImageBase64Cache:
        """获取全局图片缓存实例"""
        return cls._global_image_cache

    @classmethod
    def clear_image_cache(cls) -> None:
        """清空全局图片缓存"""
        cls._global_image_cache.clear()

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": cls._global_image_cache.size(),
            "max_size": cls._global_image_cache.max_size,
        }

    # 输出报告
    def report(self):
        print(f"Model switch count: {self.model_switch_count}")
        if self.exhausted_models:
            print(f"Exhausted models: {self.exhausted_models}")
        # 新增：输出缓存统计
        cache_stats = self.get_cache_stats()
        print(f"Image cache: {cache_stats['cache_size']}/{cache_stats['max_size']}")
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
            next_base_model_info = (
                f"Next model : \n{current_idx+2}/{models_num} Model {next_sdk_name} : {next_model_name}"
            )
            print_line(".")
            print(next_base_model_info)

    # 执行任务 - 多模型调度器支持故障转移和重试
    def execute_task(
        self,
        message_info: Dict[str, Any],
        llm_models: List[Dict[str, Any]],
        format_json: bool = False,
        validate_func: Optional[Callable[[str], tuple[bool, Any]]] = None,
        start_index: int = 0,  # 新增：起始索引
        return_detailed: bool = False,  # 是否返回详细结果
    ) -> Union[tuple[Any, int], ExecutionResult]:
        """
        执行任务 - 多模型调度器支持故障转移和重试

        Args:
            message_info: 消息信息字典
            llm_models: LLM模型列表
            format_json: 是否格式化为JSON
            validate_func: 结果验证函数
            start_index: 从第N个模型开始执行（默认0，即第一个）
            return_detailed: 是否返回详细结果（ExecutionResult对象）

        Returns:
            如果 return_detailed=False: (返回消息, token总数)
            如果 return_detailed=True: ExecutionResult对象
        """
        models_num = len(llm_models)

        # 验证起始索引
        if start_index < 0 or start_index >= models_num:
            error = ValueError(f"起始索引 {start_index} 超出范围 [0, {models_num-1}]")
            if return_detailed:
                return ExecutionResult(success=False, error=error)
            raise error

        # 从指定索引开始遍历
        for idx in range(start_index, models_num):
            model_info = llm_models[idx]
            sdk_name = model_info.get('sdk_name', 'unknown_sdk')
            model_name = model_info.get('model_name', 'unknown_model')

            # 如果是未知模型，直接结束循环
            if sdk_name == 'unknown_sdk' or model_name == 'unknown_model':
                break

            base_model_info = f"{idx+1}/{models_num} Model {sdk_name} : {model_name}"

            try:
                if self.warning_time:
                    result, total_seconds = time_monitor(
                        self.warning_time,
                        0,  # 0：不打印警告信息
                        model_info["model"].send_message,
                        [],
                        message_info,
                    )
                    return_message, total_tokens = result
                    if total_seconds > self.warning_time:
                        content = f"{sdk_name} : {model_name} execute_task took {total_seconds}s"
                        print_block("Warning: Time-consuming operation", content)
                else:
                    return_message, total_tokens = model_info["model"].send_message([], message_info)

                if format_json:
                    try:
                        return_message = convert_to_json(return_message)
                    except Exception as json_error:
                        if return_detailed:
                            # 返回详细结果，包含原始消息和错误信息
                            return ExecutionResult(
                                return_message=return_message,
                                total_tokens=total_tokens,
                                last_tried_index=idx,
                                error=json_error,
                            )
                        else:
                            # 传统模式：继续尝试下一个模型
                            content = "JSON解析失败, trying next model..."
                            print_block(base_model_info, content)
                            self.model_switch_count += 1
                            self._print_next_model_info(llm_models, idx, models_num)
                            continue

                # 验证逻辑
                if validate_func is not None:
                    is_valid, validated_value = validate_func(return_message)

                    if is_valid:
                        if validated_value:
                            if return_detailed:
                                return ExecutionResult(
                                    return_message=validated_value,
                                    total_tokens=total_tokens,
                                    success=True,
                                )
                            return validated_value, total_tokens
                    else:
                        content = "输出结果：条件校验失败, trying next model ..."
                        print_block(base_model_info, content)
                        self.model_switch_count += 1
                        # 打印下一个模型的信息
                        self._print_next_model_info(llm_models, idx, models_num)
                        continue

                # 成功返回
                if return_detailed:
                    return ExecutionResult(
                        return_message=return_message,
                        total_tokens=total_tokens,
                        success=True,
                    )
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
                    # 最后一个模型也失败了
                    if return_detailed:
                        return ExecutionResult(success=False, error=e)
                    raise e

        # 如果所有模型都失败（理论上不会到这里）
        error = Exception("All models failed.")
        if return_detailed:
            return ExecutionResult(success=False, error=error)
        raise error

    def execute_with_group(
        self,
        message_info: Dict[str, Any],
        group_name: str,
        format_json: bool = False,
        validate_func: Optional[Callable[[str], tuple[bool, Any]]] = None,
        start_index: int = 0,
        return_detailed: bool = False,  # 是否返回详细结果
    ) -> Union[tuple[Any, int], ExecutionResult]:
        """
        使用内部model_groups执行任务

        Args:
            message_info: 消息信息字典
            group_name: 模型组名称
            format_json: 是否格式化为JSON
            validate_func: 结果验证函数
            start_index: 从第N个模型开始执行

        Returns:
            如果 return_detailed=False: (返回消息, token总数)
            如果 return_detailed=True: ExecutionResult对象
        """
        if not self.model_groups:
            raise Exception("没有可用的模型组，请先初始化dispatcher")

        # 获取模型列表（这些是缓存的模型实例，保持API密钥切换状态）
        llm_models = self.model_groups.get(group_name, [])
        if not llm_models:
            raise Exception(f"未找到模型组: {group_name}")

        return self.execute_task(
            message_info,
            llm_models,
            format_json,
            validate_func,
            start_index=start_index,
            return_detailed=return_detailed,
        )

    def export_config(self, file_path: str = "dispatcher_config.json") -> None:
        """
        导出模型配置信息为JSON格式

        Args:
            file_path: 导出的JSON文件路径，默认"dispatcher_config.json"

        导出内容包括：
        - model_groups: 模型组配置（包含模型client的参数）
        - 统计信息：模型组数量、总模型数量等

        Returns:
            None: 无返回值，直接将配置写入文件
        """
        export_data = {
            "model_groups": {},
            "statistics": {
                "total_groups": len(self.model_groups),
                "total_models": 0,
                "exhausted_models": len(self.exhausted_models),
                "model_switch_count": self.model_switch_count,
                "image_cache": self.get_cache_stats(),  # 新增：缓存统计
            },
        }

        # 导出模型组配置
        for group_name, group_models in self.model_groups.items():
            export_data["model_groups"][group_name] = []
            export_data["statistics"]["total_models"] += len(group_models)

            for model_info in group_models:
                # 获取模型client实例
                model_client = model_info.get("model", None)

                # 构建模型配置信息
                model_config = {
                    "sdk_name/platform": model_info.get("sdk_name", "unknown"),
                    "model_name": model_info.get("model_name", "unknown"),
                    "base_url": getattr(model_client, 'base_url', 'unknown') if model_client else 'unknown',
                    # 导出模型client的关键参数
                    "client_config": {
                        "stream": getattr(model_client, 'stream', False) if model_client else False,
                        "stream_real": getattr(model_client, 'stream_real', False) if model_client else False,
                        "extra_body": getattr(model_client, 'extra_body', {}) if model_client else {},
                    },
                }

                export_data["model_groups"][group_name].append(model_config)

        # 保存到JSON文件
        save_json(export_data, file_path)

        return
