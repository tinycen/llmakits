#### 全局模型配置

支持通过CSV文件配置模型的高级参数，实现更精细的模型控制：

**全局配置文件格式** (`config/global_model_config.csv`):

文件格式：仅支持 .csv 和 .xlsx 格式。

> ⚠️ **重要提示**：表格文件中的布尔值（True/False）必须显式用英文双引号包裹，例如 `"True"` 或 `"""True"""`。这是为了确保CSV解析器正确处理布尔值，避免类型转换问题，同时也是为了和0/1数值区分。

| 参数名 | 说明 | 适用 platform/sdk |
| --- | --- | --- |
| `platform` | 平台名称 | - |
| `model_name` | 模型名称 | - |
| `stream` | 是否启用流式输出 | - |
| `stream_real` | 是否启用真实流式输出 | - |
| `response_format` | 响应格式 (`json` 或 `text`) | `zhipu` |
| `thinking` | 思考模式配置 | `zhipu` |
| `extra_enable_thinking` | 启用思考功能（会嵌套在extra_body中） | `modelscope`,`dashscope_openai` |
| `reasoning_effort` | 推理努力程度 | `gemini` |

**通配符匹配支持**:
- `platform` - `model_name` 格式
- 精确匹配: `dashscope,qwen3-max-preview`
- 通配符匹配 (`*` 包裹模型名称):
  - 示例：`openai,*gpt*` (匹配所有包含 gpt 的模型)
- 通用匹配 (`*` 替代模型名称):
  - 示例：`zhipu,*` (匹配智谱平台所有模型)

**使用示例**:
```python
from llmakits import load_models

# 加载带全局配置的模型
models, keys = load_models(
    'config/models_config.yaml',
    'config/keys_config.yaml',
    global_config='config/global_model_config.csv'
)
```
