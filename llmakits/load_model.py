from filekits.base_io import load_yaml
import pandas as pd
from fnmatch import fnmatch
from typing import Dict, Any, Optional
from .llm_client import BaseOpenai


def load_global_config(global_config_path: str) -> pd.DataFrame:
    """
    加载全局模型配置文件，支持CSV和XLSX格式

    Args:
        global_config_path: 全局配置文件路径（CSV或XLSX格式）

    Returns:
        pd.DataFrame: 全局配置数据框

    Raises:
        TypeError: 如果global_config_path不是字符串类型
        ValueError: 如果文件格式不支持
        FileNotFoundError: 如果文件不存在
    """

    file_ext = global_config_path.lower().split('.')[-1]
    if file_ext not in ['csv', 'xlsx']:
        raise ValueError("全局配置文件必须是.csv或.xlsx格式")

    if file_ext == 'xlsx':
        return pd.read_excel(global_config_path)
    else:
        # 默认使用CSV格式读取
        return pd.read_csv(global_config_path)


def find_model_config(global_config: pd.DataFrame, platform: str, model_name: str) -> Optional[Dict[str, Any]]:
    """
    根据平台和模型名称查找配置，支持通配符匹配

    匹配优先级：
    1. 精确匹配 (platform + model_name)
    2. 具体通配符匹配 (如 *pro*, *qwen-plus*)
    3. 通用通配符匹配 (*)

    Args:
        global_config: 全局配置数据框
        platform: 平台名称
        model_name: 模型名称

    Returns:
        Dict[str, Any]: 匹配的配置参数，如果没有匹配则返回None
    """
    # 过滤出当前平台的配置
    platform_configs = global_config[global_config['platform'] == platform]

    if platform_configs.empty:
        return None

    # 1. 首先尝试精确匹配
    exact_match = platform_configs[platform_configs['model_name'] == model_name]
    if not exact_match.empty:
        return exact_match.iloc[0].to_dict()

    # 2. 尝试具体通配符匹配（非*的通配符模式）
    specific_patterns = platform_configs[platform_configs['model_name'] != '*']
    best_match = None
    best_specificity = -1  # 匹配特异性评分，越具体的模式评分越高

    for _, row in specific_patterns.iterrows():
        config_model = row['model_name']

        # 跳过精确匹配已经处理过的情况
        if config_model == model_name:
            continue

        # 检查模型名称是否匹配（支持通配符）
        if fnmatch(model_name, config_model):
            # 计算特异性：通配符越少，特异性越高
            specificity = len(config_model) - config_model.count('*')
            if specificity > best_specificity:
                best_specificity = specificity
                best_match = row.to_dict()

    if best_match:
        return best_match

    # 3. 最后尝试通用通配符匹配 (*)
    universal_match = platform_configs[platform_configs['model_name'] == '*']
    if not universal_match.empty:
        return universal_match.iloc[0].to_dict()

    return None


def parse_model_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析模型配置，构建extra_body等参数

    参数处理规则：
    1. stream, stream_real -> 直接放入params顶层
    2. extra_enable_thinking -> 放入extra_body.extra_body.enable_thinking
    3. reasoning_effort, response_format, thinking -> 直接放入extra_body

    Args:
        config_dict: 配置字典

    Returns:
        Dict[str, Any]: 解析后的参数字典
    """
    params = {}
    extra_body = {}  # 直接传递给API的参数
    extra_body_nested = {}  # 需要嵌套在extra_body中的参数

    for key, value in config_dict.items():
        # 跳过空值
        if pd.isna(value) or value == '' or value is None:
            continue

        # 标准化布尔值：处理带引号的字符串格式
        if isinstance(value, str):
            str_value = value.strip()
            if str_value == '"""True"""' or str_value == '"True"' or str_value == 'True':
                value = True
            elif str_value == '"""False"""' or str_value == '"False"' or str_value == 'False':
                value = False

        # platform和model_name字段不添加到参数中（仅用于匹配）
        if key in ('platform', 'model_name'):
            continue

        # 处理流式输出参数
        if key in ('stream', 'stream_real'):
            params[key] = value
            continue

        # 处理extra_前缀的参数（需要嵌套在extra_body中）
        if key.startswith('extra_'):
            real_key = key[len('extra_') :]
            # 对布尔类型的extra参数进行特殊处理
            if real_key == 'enable_thinking':
                extra_body_nested[real_key] = bool(value) if isinstance(value, bool) else False
            else:
                extra_body_nested[real_key] = value
            continue

        # 处理response_format参数
        if key == 'response_format':
            if value == 'json':
                extra_body[key] = {"type": "json_object"}
            else:
                extra_body[key] = {"type": "text"}
            continue

        # 处理thinking参数
        if key == 'thinking':
            extra_body[key] = {"type": value}
            continue

        # 其他参数直接放入extra_body
        extra_body[key] = value

    # 组合最终的extra_body结构
    if extra_body_nested:
        if extra_body:
            # 两种都有，需要合并
            params['extra_body'] = {**extra_body, "extra_body": extra_body_nested}
        else:
            # 只有嵌套参数
            params['extra_body'] = {"extra_body": extra_body_nested}
    elif extra_body:
        # 只有直接参数
        params['extra_body'] = extra_body

    return params


def load_models(models_config, model_keys, global_config=None):
    """
    从YAML配置文件加载LLM模型配置并实例化模型

    Args:
        models_config: LLM模型配置文件路径或配置字典
        model_keys: LLM API凭证配置文件路径或配置字典
        global_config: 全局模型配置文件路径或DataFrame（可选）

    Returns:
        dict: 按组分类的模型实例字典

    Example:
        >>> models = load_models('config/llm_models_config.yaml', 'config/keys_config.yaml')
        >>> models = load_models('config/llm_models_config.yaml', 'config/keys_config.yaml', 'config/global_model_config.csv')
        >>> print(models.keys())  # 显示模型分组
    """
    # 检测参数类型，如果是字符串则进行加载
    if isinstance(models_config, str):
        models_config = load_yaml(models_config)

    if isinstance(model_keys, str):
        model_keys = load_yaml(model_keys)

    # 加载全局配置（如果提供）
    global_config_df = None
    if global_config:
        global_config_df = load_global_config(global_config)

    # 实例化模型缓存器
    model_instances = {}
    # 载入的模型实例
    models = {}

    for model_group, model_list in models_config.items():
        batch_models = []
        for model_info in model_list:
            sdk_name = model_info["sdk_name"]
            model_name = model_info["model_name"]
            base_url = model_keys[sdk_name]["base_url"]
            api_keys = model_keys[sdk_name]["api_keys"]

            # 使用模型名称作为唯一标识符
            model_key = f"{sdk_name}:{model_name}"

            # 检查全局缓存中是否已存在该模型实例
            if model_key in model_instances:
                batch_models.append(
                    {"sdk_name": sdk_name, "model_name": model_name, "model": model_instances[model_key]}
                )
            else:
                # 查找全局配置
                model_params = {}
                if global_config_df is not None:
                    config_dict = find_model_config(global_config_df, sdk_name, model_name)
                    if config_dict:
                        model_params = parse_model_config(config_dict)

                # 创建新的模型实例，传入配置参数
                # 注意：api_keys需要创建副本，避免多个模型共享同一个列表对象
                mini_model = BaseOpenai(
                    platform=sdk_name, base_url=base_url, api_keys=api_keys.copy(), model_name=model_name, **model_params
                )

                # 将新创建的模型实例添加到全局缓存
                model_instances[model_key] = mini_model
                batch_models.append({"sdk_name": sdk_name, "model_name": model_name, "model": mini_model})

        models[model_group] = batch_models

    return models, model_keys
