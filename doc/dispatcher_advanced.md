### 高级用法

#### 结果验证和格式化

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

#### 获取详细执行结果

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

#### 耗时警告监控

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

**耗时警告功能特点：**

1. **性能监控**: 当模型执行时间超过设定阈值时，自动显示警告信息
2. **灵活配置**: 可以根据业务需求设置不同的警告阈值
3. **不影响执行**: 警告信息不会中断任务执行，仅作为性能提示
4. **详细报告**: 警告信息包含模型名称和实际执行时间

**使用场景：**
- 监控模型响应性能，及时发现性能问题
- 在生产环境中跟踪异常耗时的请求
- 优化模型选择和配置，提高整体响应速度

#### 指定起始模型索引

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
