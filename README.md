# llmakits

用于简化大语言模型(LLM)的集成和管理。支持多模型调度、故障转移、负载均衡等功能。

支持通过YAML配置实现不同业务场景的模型组管理，日均承载数万次LLM调用（含多模态图文请求），将多模型运维复杂度降低约70%。

[![zread](icon/zread-badge.svg)](https://zread.ai/tinycen/llmakits)

## 功能特性

- 🚀 **多模型支持**: 支持OpenAI、智谱AI、DashScope、ModelScope等多个主流LLM平台；
- 🔄 **智能调度**: 内置多层故障转移和负载均衡机制；
  - 自动切换：当模型失败时，自动切换到下个可用模型；
  - 负载均衡：Token 或 请求次数 达到上限后，自动切换到下个api_key；
  - 密钥检测：自动检测并移除API密钥用尽的模型；
  - 图片处理：支持图片URL自动转base64、多图批量处理、失败域名智能降级（自动转为单图重试）、LRU缓存避免重复下载；
- 📊 **消息处理**: 强大的消息格式化、结果验证和提取功能；
- 🛡️ **错误处理**: 完善的LLM重试机制和异常处理；
- 🎯 **电商工具**: 内置电商场景专用工具集，提供带验证器的闭环工作流；
  - 标题生成：支持长度/单词数约束检查，不合格自动修改，支持程序化缩减；
  - 类目预测：支持直接预测和逐级预测两种模式，带JSON格式修复和结果验证；
  - 属性填充：支持从候选值中自动验证并填充商品属性；
  - HTML生成：自动生成商品描述HTML，自动检测并修复非法标签，支持中文过滤；
  - 选项翻译：支持商品选项多语言翻译，自动验证返回列表长度一致性；
- 📝 **流式输出**: 支持流式响应，自动转静态处理；
- 💡 **状态保持**: 模型实例缓存，避免重复实例化，保持API密钥切换状态。
- ⏱️ **性能监控**: 支持设置耗时警告阈值，监控模型响应性能，并输出响应报告；

## 安装/更新

```bash
pip install --upgrade llmakits
```

## 快速开始

### 1. 配置模型和API密钥

**模型配置文件** (`config/models_config.yaml`):
- 支持按业务场景分组配置
- 每个组可以配置多个模型，实现故障转移
- 模型会按配置顺序依次尝试，直到成功

```yaml
# 标题生成专用模型组
generate_title:
  - sdk_name: "dashscope"
    model_name: "qwen3-max-preview"

  - sdk_name: "zhipu"
    model_name: "glm-4-plus"

# 翻译专用模型组
translate_box:
  - sdk_name: "modelscope"
    model_name: "Qwen/Qwen3-32B"

  - sdk_name: "modelscope"
    model_name: "deepseek-ai/DeepSeek-V3"
```

**密钥配置文件** (`config/keys_config.yaml`):
- 支持多密钥配置，自动负载均衡
- 当密钥达到每日使用限制时，自动切换到下一个密钥
- 支持不同平台的独立配置

```yaml
# 阿里云DashScope平台
dashscope:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_keys: ["your-api-key-1", "your-api-key-2"]

# ModelScope平台
modelscope:
  base_url: "https://api-inference.modelscope.cn/v1/"
  api_keys: ["your-api-key-1", "your-api-key-2"]

```

#### 错误处理和故障转移

1. **模型级别故障转移**: 当前模型失败时，自动切换到同组的下一个模型
2. **API密钥用尽检测**: 自动检测 `API_KEY_EXHAUSTED` 异常，并移除对应的模型
3. **结果验证**: 支持自定义验证函数，验证失败时自动尝试下一个模型
4. **状态保持**: 模型实例在dispatcher中缓存，保持API密钥切换状态

#### 配置优化建议

1. **使用模型组**: 推荐使用 `execute_with_group` 方法，避免重复实例化
2. **合理配置模型顺序**: 将性能更好、更稳定的模型放在前面
3. **适当设置重试**: 根据业务需求配置模型数量和密钥数量
4. **监控切换次数**: 通过 `model_switch_count` 监控模型切换频率

#### 全局模型配置

详见 [doc/global_model_config.md](doc/global_model_config.md)。

### 2. 加载模型

```python
from llmakits import load_models

# 方式1：传入配置文件路径（字符串）
models = load_models('config/models_config.yaml', 'config/keys_config.yaml')

# 方式2：直接传入配置字典
models_config = {
    "my_models": [
        {"model_name": "gpt-3.5-turbo", "sdk_name": "openai"}
    ]
}
model_keys = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_keys": ["your-api-key"]
    }
}
models = load_models(models_config, model_keys)

# 方式3：使用全局配置（支持高级参数配置）
models = load_models(
    'config/models_config.yaml',
    'config/keys_config.yaml',
    global_config='config/global_model_config.csv'  # 可选：全局模型配置
)

# 获取模型组
my_models = models['my_models']
```

### 3. 发送消息（多模型调度）

#### 使用 ModelDispatcher（推荐）

ModelDispatcher 提供了两种使用方式，推荐使用 `execute_with_group` 方法：

**方式一：使用模型组（推荐）**

```python
from llmakits import ModelDispatcher

# 创建调度器实例并加载配置
dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')

# 准备消息
message_info = {
    "system_prompt": "你是一个 helpful 助手",
    "user_text": "请介绍一下Python编程语言"
}

# 使用模型组执行任务 - 自动管理模型状态和故障转移
result, tokens = dispatcher.execute_with_group(message_info, group_name="generate_title")
print(f"结果: {result}")
print(f"使用token数: {tokens}")
print(f"模型切换次数: {dispatcher.model_switch_count}")
```

#### 消息格式说明

`message_info` 参数支持以下字段：
- `system_prompt`: 系统提示词（可选）
- `user_text`: 用户输入文本（可选）
- `include_img`: 是否包含图片（可选，默认False）
- `img_list`: 图片URL列表（可选，默认为空列表）

基本使用示例：

```python
# 简单文本对话
message_info = {
    "system_prompt": "你是一个 helpful 助手",
    "user_text": "请介绍一下Python编程语言"
}

# 带图片的对话
message_info = {
    "system_prompt": "你是一个图像分析专家",
    "user_text": "请分析这张图片",
    "include_img": True,
    "img_list": ["https://example.com/image.jpg"]
}
# 如果include_img = True 同时 img_list 是空的，此时会报出错误。
```

**方式二：手动传入模型列表**

```python
from llmakits import ModelDispatcher

# 创建调度器实例
dispatcher = ModelDispatcher()

# 准备消息和模型列表
message_info = {
    "system_prompt": "你是一个 helpful 助手",
    "user_text": "请介绍一下Python编程语言"
}

# 执行任务
result, tokens = dispatcher.execute_task(message_info, my_models)
```

#### 高级用法：结果验证和格式化

```python
from llmakits import ModelDispatcher

# 创建调度器
dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')

# 定义结果验证函数
def validate_result(result):
    """验证结果是否包含必要的字段"""
    return "python" in result.lower() and "编程" in result

# 准备消息
message_info = {
    "system_prompt": "你是一个编程专家",
    "user_text": "请介绍Python语言的特点"
}

# 执行任务，启用JSON格式化和结果验证
result, tokens = dispatcher.execute_with_group(
    message_info,
    group_name="generate_title",
    format_json=True,           # 格式化为JSON
    validate_func=validate_result  # 验证结果
)

print(f"验证通过的结果: {result}")
print(f"使用token数: {tokens}")
```

#### 高级用法：获取详细执行结果

```python
from llmakits import ModelDispatcher
from llmakits.dispatcher import ExecutionResult

# 创建调度器
dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')

# 准备消息
message_info = {
    "system_prompt": "你是一个编程专家",
    "user_text": "请介绍Python语言的特点"
}

# 获取详细执行结果
result: ExecutionResult = dispatcher.execute_with_group(
    message_info,
    group_name="generate_title",
    return_detailed=True  # 返回详细结果
)

print(f"返回消息: {result.return_message}")
print(f"使用token数: {result.total_tokens}")
print(f"最后尝试的模型索引: {result.last_tried_index}")
print(f"是否成功: {result.success}")
if result.error:
    print(f"错误信息: {result.error}")
```

#### 高级用法：耗时警告监控

```python
from llmakits import ModelDispatcher

# 创建调度器并设置耗时警告阈值（单位：秒）
dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')
dispatcher.warning_time = 30  # 设置30秒为耗时警告阈值

# 准备消息
message_info = {
    "system_prompt": "你是一个 helpful 助手",
    "user_text": "请详细介绍Python编程语言及其生态系统"
}

# 执行任务 - 当模型执行时间超过30秒时会显示警告
result, tokens = dispatcher.execute_with_group(message_info, group_name="generate_title")
print(f"结果: {result}")
print(f"使用token数: {tokens}")

# 查看模型切换次数
print(f"模型切换次数: {dispatcher.model_switch_count}")
```

#### 高级用法：指定起始模型索引

```python
from llmakits import ModelDispatcher

# 创建调度器
dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')

# 准备消息
message_info = {
    "system_prompt": "你是一个 helpful 助手",
    "user_text": "请介绍一下Python编程语言"
}

# 从第2个模型开始执行（索引从0开始）
result, tokens = dispatcher.execute_with_group(
    message_info,
    group_name="generate_title",
    start_index=1  # 从第2个模型开始
)
print(f"结果: {result}")
print(f"使用token数: {tokens}")
```

**耗时警告功能特点：**

1. **性能监控**: 当模型执行时间超过设定阈值时，自动显示警告信息
2. **灵活配置**: 可以根据业务需求设置不同的警告阈值
3. **不影响执行**: 警告信息不会中断任务执行，仅作为性能提示
4. **详细报告**: 警告信息包含模型名称和实际执行时间

**使用场景：**
- 监控模型响应性能，及时发现性能问题
- 在生产环境中跟踪异常耗时的请求
- 优化模型选择和配置，提高整体响应速度

#### 增强版调度策略：dispatcher_with_repair

```python
from llmakits import dispatcher_with_repair

# 创建调度器
from llmakits import ModelDispatcher
dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')

# 准备消息
message_info = {
    "system_prompt": "你是一个JSON数据生成专家",
    "user_text": "请生成一个包含产品信息的JSON对象"
}

# 使用增强版调度策略 - 自动修复JSON错误
try:
    result, tokens = dispatcher_with_repair(
        dispatcher=dispatcher,
        message_info=message_info,
        group_name="generate_json",  # 主模型组名称
        validate_func=None,  # 可选：自定义验证函数
        fix_json_config={
            "group_name": "fix_json",  # 修复模型组名称
            "system_prompt": "你是一个JSON修复专家，请修复下面错误的JSON格式",
            "example_json": '{"name": "产品名称", "price": 99.99}'  # 可选：JSON示例
        }
    )
    print(f"修复后的结果: {result}")
    print(f"使用token数: {tokens}")
except Exception as e:
    print(f"所有模型和修复尝试均失败: {e}")
```

**增强版调度策略特点：**

1. **自动修复JSON错误**：当主模型返回格式错误的JSON时，自动调用修复模型组进行修复
2. **多模型支持**：每个失败的模型都会尝试修复，确保所有主模型都有机会尝试
3. **独立修复流程**：使用独立的修复调度器，避免状态混乱
4. **详细错误处理**：区分JSON错误和其他类型错误，采取不同的处理策略

**使用场景：**
- 需要生成结构化JSON数据的任务
- 对JSON格式要求严格的场景
- 希望提高任务成功率的自动化流程

### 4. 直接使用模型客户端

```python
from llmakits import BaseOpenai

# 创建模型客户端
model = BaseOpenai(
    platform="openai",
    base_url="https://api.openai.com/v1",
    api_keys=["your-api-key"],
    model_name="gpt-3.5-turbo"
)

# 方法1: 使用消息列表格式（兼容OpenAI格式）
messages = [
    {"role": "system", "content": "你是一个 helpful 助手"},
    {"role": "user", "content": "Hello!"}
]
result, tokens = model.send_message(messages)
print(f"回复: {result}")

# 方法2: 使用message_info格式（推荐）
message_info = {
    "system_prompt": "你是一个 helpful 助手",
    "user_text": "Hello!"
}
result, tokens = model.send_message([], message_info)
print(f"回复: {result}")
```

#### 高级配置选项

```python
from llmakits import BaseOpenai

# 创建带高级配置的客户端
client = BaseOpenai(
    platform="openai",
    base_url="https://api.openai.com/v1",
    api_keys=["your-api-key"],
    model_name="gpt-4o",
    stream=True,              # 启用流式输出
    stream_real=False,        # 真实流式输出
    request_timeout=60,       # 请求超时时间（秒）
    max_retries=3            # 最大重试次数
)

# 获取可用模型列表（DataFrame格式）
models_df = client.models_df()
print(f"可用模型: {models_df}")
```

#### 获取模型信息

```python
from llmakits import BaseOpenai

# 创建客户端
client = BaseOpenai(
    platform="openai",
    base_url="https://api.openai.com/v1",
    api_keys=["your-api-key"],
    model_name="gpt-4o"
)

# 获取模型列表（DataFrame格式，包含创建时间等信息）
models_df = client.models_df()
print(f"模型列表:")
print(models_df)

# 获取特定模型的创建时间
if 'created' in models_df.columns:
    gpt4o_created = models_df[models_df['id'] == 'gpt-4o']['created'].iloc[0]
    print(f"GPT-4o 创建时间: {gpt4o_created}")
```

#### 错误处理和API密钥耗尽

```python
from llmakits import BaseOpenai

client = BaseOpenai(
    platform="openai",
    base_url="https://api.openai.com/v1",
    api_keys=["your-api-key"],
    model_name="gpt-4o"
)

try:
    response, tokens = client.send_message([], message_info)
    print(f"模型响应: {response}")
except Exception as e:
    if "API key exhausted" in str(e):
        print("API密钥已耗尽，请更换密钥")
    else:
        print(f"发生错误: {e}")
```

## 高级功能

### 消息处理

```python
from llmakits.message import prepare_messages, extract_field, convert_to_json

# 准备消息
messages = prepare_messages(system="你是一个助手", user="请帮忙", assistant="好的")

# 提取并转换为JSON
json_str = '{"name": "test"} some text'
result = convert_to_json(json_str)

# 提取字段
field_value = extract_field(json_str, "name")
print(field_value)  # 输出: test

# 提取多个字段
name, age = extract_field(json_str, "name", "age")
print(name)  # 输出: test
print(age)  # 输出: None

```

### 电商工具

详见 [doc/e_commerce.md](doc/e_commerce.md)。

## 许可证

Apache 2.0 License
