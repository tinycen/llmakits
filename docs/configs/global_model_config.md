# 全局模型配置 global_model_config

支持通过表格配置模型的高级参数，实现更精细的模型控制。

**支持的数据结构**：

| 输入类型 | 说明 |
| --- | --- |
| `str` | CSV/XLSX 文件路径（仅支持 .csv 和 .xlsx 格式） |
| `pandas.DataFrame` | 直接传入数据框，字段结构与下表一致 |

**字段结构**：

| 参数名 | 说明 | 适用 platform/sdk |
| --- | --- | --- |
| `platform` | 平台名称（必填，用于匹配） | - |
| `model_name` | 模型名称（必填，支持通配符） | - |
| `stream` | 是否启用流式输出 | - |
| `stream_real` | 是否启用真实流式输出 | - |
| `extra_enable_thinking` | 启用思考功能（会嵌套在extra_body中） | `modelscope`,`dashscope_openai` |
| `reasoning_effort` | 推理努力程度（如 `none`、`low`） | `gemini` |
| `response_format` | 响应格式 (`json` 或 `text`) | `zhipu` |
| `thinking` | 思考模式配置 | `zhipu` |
| `think` | 思考模式开关（直接放入extra_body） | `ollama` |

**完整数据结构示例** (`config/global_model_config.csv`)：

```csv
platform,model_name,stream,stream_real,extra_enable_thinking,reasoning_effort,response_format,thinking,think
modelscope,Qwen/QwQ-32B,True,False,,,,
modelscope,Qwen/QVQ-72B-Preview,True,False,,,,
modelscope,Qwen/Qwen3-235B-A22B,True,False,False,,,,
modelscope,Qwen/Qwen3-32B,True,False,False,,,,
dashscope_openai,qwen3-235b-a22b,,,False,,,,
dashscope_openai,qwen3-32b,,,False,,,,
dashscope_openai,deepseek-v3.2-exp,,,False,,,,
dashscope_openai,*qwen-plus*,,,False,,,,
dashscope_openai,qwen3-vl-flash,,,False,,,,
dashscope_openai,glm-4.5,True,False,False,,,,
gemini,gemini-2.5-flash,,,,none,,,
gemini,gemini-2.5-flash-preview-09-2025,,,,none,,,
gemini,gemini-2.5-pro,,,,low,,,
zhipu,*,,,,,json,,
zhipu,*glm-4.5*,,,,,,disabled,
zhipu,*glm-4.6*,,,,,,disabled,
ollama,qwen3:32b,,,,,,,False
```

> 💡 **布尔值说明**：
> - 布尔参数（True/False）直接填写即可，无需引号；带引号（`"True"`）或 Excel 导出的三重引号（`"""True"""`）格式同样支持；
> - 请勿使用 `0`/`1` 数字代替布尔值，数字不会被解析为布尔类型；
> - 单元格留空表示不启用该参数。

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

# 方式1：传入文件路径
models, keys = load_models(
    'config/models_config.yaml',
    'config/keys_config.yaml',
    global_config='config/global_model_config.csv'
)

# 方式2：直接传入pandas DataFrame
import pandas as pd
global_config_df = pd.read_csv('config/global_model_config.csv')
models, keys = load_models(
    'config/models_config.yaml',
    'config/keys_config.yaml',
    global_config=global_config_df
)
```
