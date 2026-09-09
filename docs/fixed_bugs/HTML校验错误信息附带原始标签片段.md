# HTML校验错误信息附带原始标签片段

## 问题描述 / 需求背景

- 在电商 HTML 校验场景中，用户设置了允许的标签集合，例如：

  ```python
  allowed_tags = { "p", "bold", "strong", "ul", "ol", "li", "h1", "h2", "h3", "br", "hr" }
  ```

- 运行 `validate_html` 时仅输出：`发现未被允许的标签: h`，只显示标签名，无法看到该标签在原始 HTML 中的实际内容。
- 用户无法判断 `h` 是真实出现的裸 `<h>` 标签（如 LLM 生成了 `<h4>`/`<h5>` 之外的内容），还是正则误报（例如匹配到了类似 `<something` 的非标签文本），因此希望错误信息中附带"未被允许的标签的原始 HTML 片段"（不是完整文档，只是命中的局部结构），方便排查。

## 原因分析

- 原实现中 [check_allowed_tags](file:///c:/Users/ruoce/PycharmProjects/pypi_package/llmakits/llmakits/e_commerce/validators/html_validator.py#L5) 使用 `re.findall` + 集合差运算，只返回标签名集合，匹配到的完整片段在中间过程中被丢弃。
- `validate_html` 拿到的只有标签名（如 `h`），拼出的错误信息自然只有标签名，缺少定位信息。

## 解决方案

### 1. `check_allowed_tags` 改为返回"标签名 → 原始片段列表"的字典

将 `re.findall` 改为 `re.finditer`，逐个匹配并收集未被允许标签的完整匹配片段（[html_validator.py#L5-L26](file:///c:/Users/ruoce/PycharmProjects/pypi_package/llmakits/llmakits/e_commerce/validators/html_validator.py#L5-L26)）：

```python
def check_allowed_tags(html_string: str, allowed_tags: set[str]):
    """
    检查HTML字符串中的标签是否都在允许的标签列表中。

    Args:
        html_string: 要检查的HTML字符串
        allowed_tags: 允许使用的标签集合

    Returns:
        dict: 未被允许的标签字典 {标签名: [完整HTML片段, ...]}
    """
    # 查找所有HTML标签 (包括开始标签、结束标签和自闭合标签)
    # 这个正则表达式会匹配 <tag ...> 或 </tag> 或 <tag ... />
    # 使用 finditer 以便同时获取完整的匹配片段（用于排查）
    unallowed_tags = {}  # {标签名: [完整片段, ...]}

    for match in re.finditer(r'<\s*/?([a-zA-Z]+)[^>]*>', html_string):
        tag_name = match.group(1).lower()
        if tag_name not in allowed_tags:
            unallowed_tags.setdefault(tag_name, []).append(match.group(0))

    return unallowed_tags
```

### 2. `validate_html` 错误信息附带原始片段

在每个未允许标签后拼接其原始 HTML 片段（[html_validator.py#L101-L115](file:///c:/Users/ruoce/PycharmProjects/pypi_package/llmakits/llmakits/e_commerce/validators/html_validator.py#L101-L115)）：

```python
    # 检查标签是否被允许（仅当 allowed_tags 不为空时）
    if allowed_tags:
        unallowed_tags = check_allowed_tags(html_string, allowed_tags)
        if unallowed_tags:
            # 构建带原始片段的错误信息，方便排查是否为误报
            tag_details = []
            for tag_name, fragments in unallowed_tags.items():
                # 去重并限制显示数量，避免过长
                unique_fragments = list(dict.fromkeys(fragments))
                shown = ', '.join(repr(f) for f in unique_fragments[:3])
                if len(unique_fragments) > 3:
                    shown += f", ...等共{len(unique_fragments)}处"
                tag_details.append(f"{tag_name}({shown})")
            detail = '; '.join(sorted(tag_details))
            error_messages.append(f"发现未被允许的标签: {detail}")
```

设计要点：

- 使用 `dict.fromkeys` 去重（保留出现顺序）
- 每个标签最多展示 3 个片段，超过则追加 `...等共N处`，避免错误信息过长
- 片段使用 `repr()` 展示，特殊字符转义清晰可读
- `validate_html` 原有的 `print(error_messages)` 会一并打印这些片段

### 3. 调用方兼容性确认

通过 Grep 检索 `check_allowed_tags` 在整个项目中的引用，确认只有两处：

- `validate_html` 内部调用（返回值消费方式已同步修改）
- `llmakits/e_commerce/validators/__init__.py` 中的导入与 `__all__` 导出（无返回值消费）

因此返回类型从 `set[str]` 变更为 `dict[str, list[str]]` 对外部无影响。

## 效果示例

修改前：

```
发现未被允许的标签: h
```

修改后（示例）：

```
发现未被允许的标签: h('<h class="title">', '</h>')
```

根据片段即可直接判断是真实的 `<h>` 裸标签，还是形如 `<something` 的正则误匹配，无需查看完整 HTML 内容。

## 相关文件

| 文件 | 说明 |
|------|------|
| `llmakits/e_commerce/validators/html_validator.py` | `check_allowed_tags` 返回结构改为 `{标签名: [原始片段, ...]}`；`validate_html` 错误信息附带片段并做去重/截断 |
| `llmakits/e_commerce/validators/__init__.py` | 仅导出 `check_allowed_tags`，未消费返回值，无需改动 |
