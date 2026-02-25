"""
重试配置模块
定义所有与重试相关的关键词配置
"""

# 图片下载相关的错误关键词列表
IMAGE_DOWNLOAD_ERROR_KEYWORDS = [
    "Download the media resource timed out",
    "Unable to download the media",  # modelscope
    "Failed to download multimodal content",
    "Download multimodal file timed out",
]
MIN_LIMIT_ERROR_KEYWORDS = [
    "Rate limit exceeded: free-models-per-min",  # openrouter
    "is temporarily rate-limited upstream",  # openrouter
]

# 默认的重试关键词列表
DEFAULT_RETRY_KEYWORDS = [
    "Too many requests",
    "频繁操作，请稍后重试",  # gitcode
    "Allocated quota exceeded, please increase your quota limit",
    "Max retries exceeded with url",
    "Requests rate limit exceeded, please try again later",
    "Free credits temporarily have rate limits",  # vercel
    "experiencing high traffic right now! Please try again soon",  # cerebras
]

DEFAULT_RETRY_KEYWORDS.extend(MIN_LIMIT_ERROR_KEYWORDS)
DEFAULT_RETRY_KEYWORDS.extend(IMAGE_DOWNLOAD_ERROR_KEYWORDS)

# API限流相关的重试关键词列表
DEFAULT_RETRY_API_KEYWORDS = [
    "Request limit exceeded",  # modelscope
    "You have exceeded today",  # modelscope
    "We have to rate limit you",  # modelscope
    "make sure your associated Aliyun account is real-name verified",  # modelscope
    "The free tier of the model has been exhausted",  # dashscope
    "Rate limit exceeded: free-models-per-day-high-balance",  # openrouter
    "API key USD spend limit exceeded",  # openrouter
    "You exceeded your current quota",  # gemini
    "You have exceeded your monthly included credits",  # huggingface
    "Tokens per day limit exceeded",  # cerebras_openai
    "免费使用额度已用完",  # gitcode , modelscope
    # 模型不存在
    "not_found_error",  # cerebras_openai
    "no provider supported",  # modelscope
]
