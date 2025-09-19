# llmakits

一个功能强大的Python工具包，用于简化大语言模型(LLM)的集成和管理。支持多模型调度、故障转移、负载均衡等功能。

## 功能特性

- 🚀 **多模型支持**: 支持OpenAI、智谱AI、DashScope、ModelScope等多个主流LLM平台
- 🔄 **智能调度**: 内置模型故障转移和负载均衡机制
- 🔑 **密钥管理**: 灵活的API密钥配置和管理
- 📊 **消息处理**: 强大的消息格式化、验证和提取功能
- 🛡️ **错误处理**: 完善的重试机制和异常处理
- 📝 **流式输出**: 支持流式响应处理
- 🎯 **电商工具**: 内置电商场景专用工具集

## 安装

```bash
pip install llmakits
```

更新：

```bash
pip install --upgrade llmakits
```

## 快速开始

### 1. 配置模型和API密钥

创建配置文件 `config/models_config.yaml`：

```yaml
Models_config:
  my_models:
    - sdk_name: "openai"
      model_name: "gpt-3.5-turbo"
    - sdk_name: "zhipu"
      model_name: "glm-4-flash"
```

创建配置文件 `config/keys_config.yaml`：

```yaml
openai:
  base_url: "https://api.openai.com/v1"
  api_keys:
    - "your-openai-api-key-1"
    - "your-openai-api-key-2"

zhipu:
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  api_keys:
    - "your-zhipu-api-key"
```

### 2. 加载模型

```python
from llmakits import load_models

# 加载配置好的模型
models = load_models('config/models_config.yaml', 'config/keys_config.yaml')

# 获取模型组
my_models = models['my_models']
```

### 3. 发送消息（多模型调度）

#### 使用新的 ModelDispatcher 类（推荐）

```python
from llmakits.dispatcher import ModelDispatcher

# 创建调度器实例
dispatcher = ModelDispatcher()

# 准备消息
message_info = {
    "system": "你是一个 helpful 助手",
    "user": "请介绍一下Python编程语言"
}

# 执行任务
result, tokens = dispatcher.execute_task(message_info, my_models)
print(f"结果: {result}")
print(f"使用token数: {tokens}")

# 获取模型切换次数
switch_count = dispatcher.model_switch_count
print(f"模型切换次数: {switch_count}")

```

#### 使用兼容函数（旧版本）

```python
from llmakits.dispatcher import execute_task

# 准备消息
message_info = {
    "system": "你是一个 helpful 助手",
    "user": "请介绍一下Python编程语言"
}

# 执行任务
result, tokens, switch_count = execute_task(message_info, my_models)
print(f"结果: {result}")
print(f"使用token数: {tokens}")
print(f"模型切换次数: {switch_count}")
```

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

# 发送消息
messages = [
    {"role": "system", "content": "你是一个 helpful 助手"},
    {"role": "user", "content": "Hello!"}
]

result, tokens = model.send_message(messages)
print(f"回复: {result}")
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

#### 基础工具函数

```python
from llmakits.e_commerce import contains_chinese, remove_chinese, shorten_title, validate_html

# 使用简单函数
result = contains_chinese("智能手机")  # 返回 True
title = shorten_title("一个很长的商品标题", 50)  # 缩减到50字符

# HTML验证
allowed_tags = {'div', 'p', 'span', 'strong', 'em'}
is_valid, error_msg = validate_html("<div>内容</div>", allowed_tags)
```

#### 高级电商功能

```python
from llmakits.dispatcher import ModelDispatcher
from llmakits.e_commerce.kit import generate_title, predict_category, translate_options, validate_html_fix

# 创建调度器
dispatcher = ModelDispatcher()

# 生成优化商品标题
system_prompt = "你是一个电商标题优化专家"
title = generate_title(
    dispatcher=dispatcher,
    title="原始商品标题",
    llm_models=my_models,
    system_prompt=system_prompt,
    max_length=225,
    min_length=10
)

# 预测商品类目
cat_tree = {}  # 类目树数据
categories = predict_category(
    dispatcher=dispatcher,
    title="商品标题",
    cat_tree=cat_tree,
    system_prompt="预测商品类目",
    llm_models=my_models
)

# 翻译商品选项
options = ["红色", "蓝色", "绿色"]
translated = translate_options(
    dispatcher=dispatcher,
    title="商品标题",
    options=options,
    to_lang="english",
    llm_models=my_models,
    system_prompt="翻译商品选项"
)

# 验证并修复HTML
html_content = "<div>内容</div><script>alert('test')</script>"
allowed_tags = {'div', 'p', 'span'}
fixed_html = validate_html_fix(
    dispatcher=dispatcher,
    html_string=html_content,
    allowed_tags=allowed_tags,
    llm_models=my_models,
    prompt="修复HTML中的不允许标签"
)
```

## 配置说明

### 模型配置 (`models_config.yaml`)

按功能分组配置模型，支持为不同场景配置不同的模型组合：

```yaml
Models_config:
  # 标题生成专用模型组
  generate_title:
    - sdk_name: "dashscope"
      model_name: "qwen3-max-preview"

  # 翻译专用模型组
  translate_box:
    - sdk_name: "modelscope"
      model_name: "Qwen/Qwen3-32B"
```

### 密钥配置 (`keys_config.yaml`)

支持多密钥配置，自动切换和负载均衡：

```yaml
platform_name:
  base_url: "api-endpoint-url"
  api_keys:
    - "api-key-1"
    - "api-key-2"
```

## 错误处理

llmakits内置了完善的错误处理机制：

- **自动重试**: 请求失败时自动重试，最多5次
- **密钥切换**: API密钥失效时自动切换到备用密钥
- **模型切换**: 当前模型失败时自动尝试下一个可用模型
- **异常捕获**: 详细的异常信息和处理建议

## 许可证

Apache 2.0 License
