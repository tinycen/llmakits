# 模型配置 models_config

模型配置定义了按业务场景分组的模型列表，每个组内的模型按配置顺序依次尝试，实现故障转移。

**支持的数据结构**：

| 输入类型 | 说明 |
| --- | --- |
| `str` | YAML 文件路径 |
| `dict` | 配置字典，结构与 YAML 文件一致 |

**字段结构（YAML/字典）**：

```yaml
# 组名（业务场景名称）
generate_title:
  - sdk_name: "dashscope"           # 平台/SDK名称，需与密钥配置中的平台名称对应
    model_name: "qwen3-max-preview" # 模型名称，需为该平台支持的模型标识

  - sdk_name: "zhipu"
    model_name: "glm-4-plus"

translate_box:
  - sdk_name: "modelscope"
    model_name: "Qwen/Qwen3-32B"
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 组名 | `str` | 业务场景名称，作为模型组的键，调用时通过 `group_name` 指定 |
| `sdk_name` | `str` | 平台/SDK名称，必须与密钥配置（keys_config）中的平台名称一致 |
| `model_name` | `str` | 模型名称，须为该平台支持的模型标识 |

**配置说明**：

1. **模型组**: 每个组可以配置多个模型，实现故障转移；
2. **模型顺序**: 模型会按配置顺序依次尝试，直到成功；建议将性能更好、更稳定的模型放在前面；
3. **模型复用**: 相同 `sdk_name + model_name` 的模型实例会被缓存复用，避免重复实例化；
4. **参数联动**: 模型的高级参数（流式输出、思考模式等）通过 [global_model_config.md](global_model_config.md) 配置。

**使用示例**：

```python
from llmakits import load_models

# 方式1：传入YAML文件路径
models, keys = load_models('config/models_config.yaml', 'config/keys_config.yaml')

# 方式2：直接传入配置字典
models_config = {
    "generate_title": [
        {"sdk_name": "dashscope", "model_name": "qwen3-max-preview"},
        {"sdk_name": "zhipu", "model_name": "glm-4-plus"},
    ]
}
models, keys = load_models(models_config, 'config/keys_config.yaml')
```
