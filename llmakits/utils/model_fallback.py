from .normalize_error import ResponseError


def should_stop_model_fallback(response_error: ResponseError, error_message: str) -> bool:
    """判断是否应停止模型切换并立即抛出异常。"""
    non_fallback_error_tags = {
        "图片下载转base64失败",
    }
    non_fallback_keywords = (
        "图片",
        "base64",
        "强制base64域名图片转换失败",
    )

    if response_error.error_tag in non_fallback_error_tags:
        return True
    return any(keyword in error_message for keyword in non_fallback_keywords)
