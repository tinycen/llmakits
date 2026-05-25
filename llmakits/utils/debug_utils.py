import os
import sys
from typing import Optional


def trigger_breakpoint(exception: Optional[BaseException] = None) -> None:
    """
    触发断点。
    1. 如果设置了环境变量 LLMAKITS_BREAKPOINT (1, true, yes, y, on)，则强制触发。
    2. 如果检测到有调试器在运行 (sys.gettrace())，则触发。
    3. 同一个异常对象最多只触发一次断点，避免嵌套 except 重复中断。
    """
    if exception is not None and getattr(exception, "_llmakits_breakpoint_triggered", False):
        return

    force_break = os.getenv("LLMAKITS_BREAKPOINT", "").strip().lower() in {"1", "true", "yes", "y", "on"}
    is_debugging = sys.gettrace() is not None

    if force_break or is_debugging:
        if exception is not None:
            setattr(exception, "_llmakits_breakpoint_triggered", True)
        breakpoint()
