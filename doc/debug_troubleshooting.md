# Debug 常见问题说明

## 没有启动调试

### 现象

- 已设置 `dispatcher.debug = True`
- 运行时报了 "原始响应中没有choices"
- 但 PyCharm 没有在异常点停住，只打印了错误并结束

这在有外层 `try-except` 时是常见现象，不是库一定失效。

---

### 原因拆解

1. **try-except 把异常捕获了**
   你外层代码会吞掉异常，异常变成"已处理异常"，IDE 默认不会按"未处理异常"中断。

2. **PyCharm 异常断点配置只勾了"终止时"**
   只在程序因未捕获异常退出时断。
   有 `except` 时，程序不会因该异常终止，不触发 debug 断点。
   修改路径： PyCharm 运行 -> 查看断点 -> Python 异常断点 -> 任何异常，同时勾选以下：
   - **引发时**
   - **终止时**
   这样才能同时对库进行调试，而不是只在"终止时"中断。

3. **debug=True 的触发条件**
   库内部在 debug 模式会调用 `trigger_breakpoint(e)`，最终执行 `breakpoint()`。
   但若 `PYTHONBREAKPOINT=0`，`breakpoint()` 会被禁用。

4. **导入版本偏差（高频问题）**
   脚本可能跑的是 `site-packages` 里的旧包，不是你正在看的源码版本。

---

### 正确用法（推荐）

1. `dispatcher.debug = True`
2. PyCharm 勾选异常断点"引发时"（可同时保留"终止时"）
3. 运行配置加环境变量：`LLMAKITS_BREAKPOINT=1`（可选，但强烈建议）
4. 若要让 IDE 一定停住，临时不要吞异常：

```python
except Exception:
    raise
```

---

### 最小可用调试配置

LLMAKITS_BREAKPOINT = 1 表示启用 debug 断点。

```
PYTHONUNBUFFERED=1;LLMAKITS_BREAKPOINT=1
```

**PyCharm:**
- Python 异常断点 -> 任何异常 -> **引发时** 勾选
- **终止时** 可保留勾选

---

### 排查清单（按优先级）

1. **打印导入路径，确认源码版本一致**

```python
import llmakits, llmakits.llm_client, llmakits.utils.debug_utils
print(llmakits.__file__)
print(llmakits.llm_client.__file__)
print(llmakits.utils.debug_utils.__file__)
```

2. **检查是否禁用了 `breakpoint()`**

```python
import os
print(os.getenv("PYTHONBREAKPOINT"))
```

若输出 `0`，会导致断点函数不生效。

3. **确认 debug 真正开启**

```python
print(dispatcher.debug)
```

4. **临时去掉外层 try-except 验证一次**
   若去掉后能断住，说明就是"异常被捕获"导致的 IDE 行为。

---

### 一句话总结

异常被外层捕获 + PyCharm 只在"终止时"中断，所以看起来像"debug 没启动"；实际应通过"引发时"断点、`LLMAKITS_BREAKPOINT=1` 和不吞异常来调试。
