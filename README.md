# llmakits

一个功能强大的Python工具包，用于简化大语言模型(LLM)的集成和管理。支持多模型调度、故障转移、负载均衡等功能。

## 功能特性

- 🚀 **多模型支持**: 支持OpenAI、智谱AI、DashScope、ModelScope等多个主流LLM平台；
- 🔄 **智能调度**: 内置模型故障转移和负载均衡机制；
  - 自动切换：当模型失败时，自动切换到下个可用模型；
  - 负载均衡：Token 或 请求次数 达到上限后，自动切换到下个api_key；
  - API密钥用尽处理：自动检测并移除API密钥用尽的模型；
- 📊 **消息处理**: 强大的消息格式化、验证和提取功能；
- 🛡️ **错误处理**: 完善的重试机制和异常处理；
- 📝 **流式输出**: 支持流式响应处理；
- 🎯 **电商工具**: 内置电商场景专用工具集；
- 💡 **状态保持**: 模型实例缓存，避免重复实例化，保持API密钥切换状态。

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

**密钥配置文件** (`config/keys_config.yaml`):
- 支持多密钥配置，自动负载均衡
- 当密钥达到每日使用限制时，自动切换到下一个密钥
- 支持不同平台的独立配置

```yaml
platform_name:
  base_url: "api-endpoint-url"
  api_keys:
    - "api-key-1"
    - "api-key-2"
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

### 2. 加载模型

```python
from llmakits import load_models

# 加载配置好的模型
models = load_models('config/models_config.yaml', 'config/keys_config.yaml')

# 获取模型组
my_models = models['my_models']
```

### 3. 发送消息（多模型调度）

#### 使用 ModelDispatcher（推荐）

ModelDispatcher 提供了两种使用方式，推荐使用 `execute_with_group` 方法：

**方式一：使用模型组（推荐）**

```python
from llmakits.dispatcher import ModelDispatcher

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
from llmakits.dispatcher import ModelDispatcher

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
from llmakits.dispatcher import ModelDispatcher

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

电商工具函数现在支持使用模型组名称，更加简洁：

```python
from llmakits.e_commerce import generate_title, generate_html, fill_attr,predict_category, translate_options, validate_html_fix

# 创建调度器 - 加载配置
dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')

# 生成优化商品标题
system_prompt = "你是一个电商标题优化专家"
title = generate_title(
    dispatcher=dispatcher,
    title="原始商品标题",
    product_info="这是一个需要优化的商品，包含详细的产品描述和特点",
    system_prompt=system_prompt,
    group_name="generate_title",  # 使用模型组名称
    min_length=10,
    max_length=225,
    min_word=2,      # 标题最少包含2个单词
    max_attempts=3   # 最大重试/修改次数
)

# 预测商品类目
cat_tree = {}  # 类目树数据
categories = predict_category(
    dispatcher=dispatcher,
    title="商品标题",
    cat_tree=cat_tree,
    system_prompt="预测商品类目",
    group_name="generate_title"  # 使用模型组名称
)

# 翻译商品选项
options = ["红色", "蓝色", "绿色"]
translated = translate_options(
    dispatcher=dispatcher,
    title="商品标题",
    options=options,
    to_lang="english",
    group_name="translate_box",  # 使用模型组名称
    system_prompt="翻译商品选项"
)

# 验证并修复HTML
html_content = "<div>内容</div><script>alert('test')</script>"
allowed_tags = {'div', 'p', 'span'}
fixed_html = validate_html_fix(
    dispatcher=dispatcher,
    html_string=html_content,
    allowed_tags=allowed_tags,
    group_name="generate_title",  # 使用模型组名称
    system_prompt="修复HTML中的不允许标签"
)

# 生成HTML商品描述（自动修复错误）
product_info = """
产品名称：智能手表
特点：防水、心率监测、GPS定位
材质：不锈钢表带，强化玻璃表面
适用场景：运动、日常佩戴
"""

html_description = generate_html(
    dispatcher=dispatcher,
    product_info=product_info,
    generate_prompt="你是一个电商产品描述专家，请根据产品信息生成美观的HTML格式描述，包含标题、段落、列表等结构",
    fix_prompt="修复HTML中的不允许标签，确保HTML格式正确",
    generate_group="generate_html",  # 生成HTML使用的模型组
    fix_group="fix_html",       # 修复HTML使用的模型组
    allowed_tags={'div', 'p', 'h1', 'h2', 'h3', 'ul', 'li', 'strong', 'em', 'span', 'br'}
)

# 填充属性值

# 准备消息信息
message_info = {
    "system_prompt": "你是一个商品属性填充专家，请根据商品信息填充相应的属性值",
    "user_text": "请为智能手表填充颜色属性"
}

# 定义可选项列表
color_choices = ["黑色", "白色", "蓝色", "红色", "粉色", "金色", "银色"]

# 使用fill_attr函数填充属性
filled_result = fill_attr(
    dispatcher=dispatcher,
    message_info=message_info,
    group="generate_title",  # 使用模型组名称
    choices=color_choices    # 可选值列表，用于验证结果
)

print(f"填充的属性结果: {filled_result}")
```

## 许可证

Apache 2.0 License
