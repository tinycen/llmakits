# 密钥配置 keys_config

密钥配置定义了各平台的API凭证。支持多密钥负载均衡，当密钥达到使用限制时自动切换到下一个密钥。

**支持的数据结构**：

| 输入类型 | 说明 |
| --- | --- |
| `str` | YAML 文件路径 |
| `dict` | 配置字典，结构与 YAML 文件一致 |
| `pandas.DataFrame` | 密钥数据框，字段结构见下表 |

**字段结构（YAML/字典）**：

```yaml
# 平台名称（与模型配置中的 sdk_name 对应）
dashscope:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  # API基础地址
  api_keys: ["your-api-key-1", "your-api-key-2"]                  # API密钥列表

modelscope:
  base_url: "https://api-inference.modelscope.cn/v1/"
  api_keys: ["your-api-key-1", "your-api-key-2"]
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 平台名称 | `str` | 作为字典的键，必须与模型配置（models_config）中的 `sdk_name` 一致 |
| `base_url` | `str` | API基础地址 |
| `api_keys` | `list[str]` | API密钥列表；多个密钥自动负载均衡，达到限制后自动切换 |

**字段结构（DataFrame）**：

支持两种列格式（自动检测）：

格式一：`api_keys` 列（复数），每行一个平台：

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| `platform` | `str` | 平台名称，对应 YAML 格式中的顶层键 |
| `base_url` | `str` | API基础地址 |
| `api_keys` | `list` 或 `str` | 密钥列表；为字符串时以 `;`、`|` 或 `,` 分隔多个密钥 |

格式二：`api_key` 列（单数），每行一个密钥，同一平台多行自动聚合：

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| `platform` | `str` | 平台名称，同一平台可出现在多行 |
| `base_url` | `str` | API基础地址，取该平台第一个非空值 |
| `api_key` | `str` | 单个API密钥（也支持分隔符字符串），同一平台多行自动合并为密钥列表 |

> 空密钥会被自动过滤；`platform` 为空的行会被跳过；缺少 `api_keys` 和 `api_key` 列时会抛出 `ValueError`。

**使用示例**：

```python
import pandas as pd
from llmakits import load_models

# 方式1：传入YAML文件路径
models, keys = load_models('config/models_config.yaml', 'config/keys_config.yaml')

# 方式2：直接传入配置字典
keys_config = {
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_keys": ["your-api-key-1", "your-api-key-2"]
    }
}
models, keys = load_models('config/models_config.yaml', keys_config)

# 方式3：传入pandas DataFrame（api_keys 为列表，适合程序化构建）
keys_df = pd.DataFrame({
    "platform": ["dashscope", "modelscope"],
    "base_url": ["https://dashscope.aliyuncs.com/compatible-mode/v1",
                 "https://api-inference.modelscope.cn/v1/"],
    "api_keys": [["your-api-key-1", "your-api-key-2"], ["your-api-key-3"]]
})
models, keys = load_models('config/models_config.yaml', keys_df)

# 方式4：传入pandas DataFrame（api_keys 为分隔符字符串，适合从CSV/Excel读取）
keys_df = pd.read_csv('config/keys_config.csv')
# CSV内容示例：
# platform,base_url,api_keys
# dashscope,https://dashscope.aliyuncs.com/compatible-mode/v1,"key-1;key-2"
# modelscope,https://api-inference.modelscope.cn/v1/,key-3
models, keys = load_models('config/models_config.yaml', keys_df)

# 方式5：传入pandas DataFrame（api_key 单列，每行一个密钥，同平台多行自动聚合）
keys_df = pd.DataFrame({
    "platform": ["dashscope", "dashscope", "modelscope"],
    "base_url": ["https://dashscope.aliyuncs.com/compatible-mode/v1",
                 "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 "https://api-inference.modelscope.cn/v1/"],
    "api_key": ["your-api-key-1", "your-api-key-2", "your-api-key-3"]
})
# 等价于 dashscope 配置了 ["your-api-key-1", "your-api-key-2"] 两个密钥
models, keys = load_models('config/models_config.yaml', keys_df)
```
