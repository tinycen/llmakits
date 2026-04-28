### 电商工具

#### 基础工具函数

中文字符检测，字符长度检测，HTML验证

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

##### 优化商品标题

```python
from llmakits.e_commerce import generate_title
from llmakits import ModelDispatcher

dispatcher = ModelDispatcher('config/models_config.yaml', 'config/keys_config.yaml')

system_prompt = "你是一个电商标题优化专家"
title = generate_title(
    dispatcher=dispatcher,
    title="原始商品标题",
    product_info="这是一个需要优化的商品，包含详细的产品描述和特点",
    system_prompt=system_prompt,
    group_name="generate_title",
    min_length=10,
    max_length=225,
    min_word=2,
    max_attempts=3
)
```

##### 预测商品类目

```python
from llmakits.e_commerce import predict_cat_direct

category_all = [
    {"cat_id": "1", "cat_name": "类目1"},
    {"cat_id": "2", "cat_name": "类目2"}
]

categories = predict_cat_direct(
    dispatcher=dispatcher,
    product={"title": "商品标题", "image_url": ""},
    predict_config={
        "system_prompt": "你是一个商品分类专家，请根据商品标题预测合适的商品类目",
        "category_all": category_all
    }
)
```

带 JSON 修复功能（自动修复错误的JSON格式）：

```python
categories_with_fix = predict_cat_direct(
    dispatcher=dispatcher,
    product={"title": "护发喷雾", "image_url": "https://example.com/image.jpg"},
    predict_config={
        "system_prompt": "你是一个商品分类专家，请根据商品标题和图片预测合适的商品类目",
        "category_all": category_all
    },
    fix_json_config={
        "system_prompt": "你是一个JSON格式修复专家，请修复下面错误的JSON格式",
        "group_name": "fix_json"
    }
)
```

##### 梯度预测商品类目（逐级预测）

```python
from llmakits.e_commerce import predict_cat_gradual

categories_gradual = predict_cat_gradual(
    dispatcher=dispatcher,
    product={"title": "智能手机", "image_url": "https://example.com/image.jpg"},
    cat_tree=cat_tree,
    predict_config={
        "system_prompt": "你是一个商品分类专家，请根据商品标题和图片逐级预测合适的商品类目",
        "group_name": "predict_category"
    },
    fix_json_config={
        "system_prompt": "你是一个JSON格式修复专家，请修复下面错误的JSON格式",
        "group_name": "fix_json"
    }
)
```

##### 翻译商品选项

```python
from llmakits.e_commerce import translate_options

options = ["红色", "蓝色", "绿色"]
translated = translate_options(
    dispatcher=dispatcher,
    title="商品标题",
    options=options,
    to_lang="english",
    group_name="translate_box",
    system_prompt="翻译商品选项"
)
```

##### 生成HTML商品描述

```python
from llmakits.e_commerce import generate_html

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
    generate_group="generate_html",
    fix_group="fix_html",
    allowed_tags={'div', 'p', 'h1', 'h2', 'h3', 'ul', 'li', 'strong', 'em', 'span', 'br'}
)
```

##### 填充属性值

```python
from llmakits.e_commerce import fill_attr

message_info = {
    "system_prompt": "你是一个商品属性填充专家，请根据商品信息填充相应的属性值",
    "user_text": "请为智能手表填充颜色属性"
}

color_choices = ["黑色", "白色", "蓝色", "红色", "粉色", "金色", "银色"]

filled_result = fill_attr(
    dispatcher=dispatcher,
    message_info=message_info,
    group="generate_title",
    choices=color_choices
)

print(f"填充的属性结果: {filled_result}")
```
