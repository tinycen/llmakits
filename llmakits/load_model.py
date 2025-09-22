from filekits.base_io.load import load_yaml
from llmakits.llm_client import BaseOpenai


def load_models(models_config, model_keys):
    """
    从YAML配置文件加载LLM模型配置并实例化模型

    Args:
        models_config_path (str): LLM模型配置文件路径
        model_keys_path (str): LLM API凭证配置文件路径

    Returns:
        dict: 按组分类的模型实例字典

    Example:
        >>> models= load_models('config/llm_models_config.yaml', 'config/keys_config.yaml')
        >>> print(models.keys())  # 显示模型分组
    """
    # 检测参数类型，如果是字符串则进行加载
    if isinstance(models_config, str):
        model_config = load_yaml(models_config)
        models_config = model_config["Models_config"]

    if isinstance(model_keys, str):
        model_keys = load_yaml(model_keys)
        model_api_keys = model_keys["Api_keys"]
    else:
        model_api_keys = model_keys
    """
    {'Models_config': {'option_type': [{'model_name': 'Qwen/Qwen2.5-32B-Instruct', 'sdk_name': 'modelscope'},
    {'model_name': 'glm-4-flash-250414', 'sdk_name': 'zhipu'}]}}
    """
    # 实例化模型缓存器
    model_instances = {}
    # 载入的模型实例
    models = {}

    for model_group, model_list in models_config.items():
        batch_models = []
        for model_info in model_list:
            sdk_name = model_info["sdk_name"]
            model_name = model_info["model_name"]
            base_url = model_api_keys[sdk_name]["base_url"]
            api_keys = model_api_keys[sdk_name]["api_keys"]

            # 使用模型名称作为唯一标识符
            model_key = f"{sdk_name}:{model_name}"

            # 检查全局缓存中是否已存在该模型实例
            if model_key in model_instances:
                batch_models.append(
                    {"sdk_name": sdk_name, "model_name": model_name, "model": model_instances[model_key]}
                )
            else:
                # 创建新的模型实例
                mini_model = BaseOpenai(sdk_name, base_url, api_keys, model_name)

                # 将新创建的模型实例添加到全局缓存
                model_instances[model_key] = mini_model
                batch_models.append({"sdk_name": sdk_name, "model_name": model_name, "model": mini_model})

        models[model_group] = batch_models

    return models, model_api_keys
