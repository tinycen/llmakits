# PromptManager 提示词管理器

`PromptManager` 用于加载和管理 Prompt 模板文件，支持从指定文件夹中批量读取 `.md` 格式的提示词模板。

## 目录结构规范

推荐将提示词文件按以下结构组织：

```
your_prompts_folder/
├── General/              # 通用提示词（必选）
│   ├── prompt1.md
│   └── prompt2.md
└── YourSubfolder/        # 业务场景专用提示词（可选）
    ├── prompt3.md
    └── prompt4.md
```

- `General` 文件夹：存放通用提示词，会始终被加载
- 子文件夹（如 `YourSubfolder`）：存放特定业务场景的提示词，可通过 `subfolder_name` 参数指定加载

## 基本用法

### 初始化 PromptManager

```python
from llmakits import PromptManager

# 加载基础提示词（仅 General 文件夹）
prompt_manager = PromptManager('path/to/your_prompts_folder')

# 加载基础提示词 + 指定子文件夹
prompt_manager = PromptManager('path/to/your_prompts_folder', subfolder_name='YourSubfolder')
```

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `base_folder` | `StrPath` | 存放 prompt 文件的基础文件夹路径 |
| `subfolder_name` | `str \| None` | 可选的子文件夹名称，为 `None` 时仅加载 General 文件夹 |

### 获取提示词

```python
# 通过 key 获取提示词内容
prompt_content = prompt_manager.get_prompt('prompt1')
```
**异常：** 当指定的 key 不存在时抛出 `KeyError`


## 注意事项

1. 提示词文件必须为 `.md` 格式
2. 不同文件夹下不允许出现相同文件名的提示词文件（会抛出 `KeyError`）
3. 建议使用有意义的 key 命名提示词文件，便于管理和查找
