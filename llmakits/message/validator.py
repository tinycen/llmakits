"""
消息验证器
负责验证内容的有效性
"""

from dataclasses import dataclass


@dataclass
class FileSignature:
    """文件类型签名"""

    signature: str  # base64特征
    description: str  # 描述


# 定义不同文件类型的base64特征
BASE64_SIGNATURES = {
    # 图片格式
    "jpeg": FileSignature("/9j/", "JPEG图片"),
    "png": FileSignature("iVBORw0KGgo", "PNG图片"),
    "gif": FileSignature("R0lGODlh", "GIF图片"),
    "webp": FileSignature("UklGR", "WebP图片"),
    "bmp": FileSignature("Qk0", "BMP图片"),
    "svg": FileSignature("PHN2Zy", "SVG图片"),
    "avif": FileSignature("AAAAIGZ0eXBhdmlm", "AVIF图片"),
    "heic": FileSignature("AAAAGGZ0eXBoZWlj", "HEIC图片"),
    # 文档格式
    "html": FileSignature("PCFET0NUWVBFIGh0bWw+", "HTML文档"),
}

# 图片签名列表（方便遍历）
IMAGE_SIGNATURES = [
    BASE64_SIGNATURES["jpeg"],
    BASE64_SIGNATURES["png"],
    BASE64_SIGNATURES["gif"],
    BASE64_SIGNATURES["webp"],
    BASE64_SIGNATURES["bmp"],
    BASE64_SIGNATURES["svg"],
    BASE64_SIGNATURES["avif"],
    BASE64_SIGNATURES["heic"],
]


def validate_base64_content(base64_str: str, expected_type: str = "image") -> tuple[bool, str]:
    """
    验证base64字符串的内容类型

    Args:
        base64_str: base64编码的字符串
        expected_type: 期望的内容类型，默认为"image"，可以是"image"或"any"

    Returns:
        (是否有效, 错误信息)
    """
    if not base64_str:
        return False, "base64字符串为空"

    # 当指定为图片类型时，检查是否为HTML（应该报错）
    html_sig = BASE64_SIGNATURES["html"]
    if expected_type == "image" and base64_str.startswith(html_sig.signature):
        return False, f"检测到 base64 内容为：{html_sig.description}，请检查URL是否为有效的图片链接(或者文件下载失败)"

    # 如果不限制类型，直接通过
    if expected_type == "any":
        return True, ""

    # 验证是否为图片类型
    if expected_type == "image":
        for sig in IMAGE_SIGNATURES:
            if base64_str.startswith(sig.signature):
                return True, ""
        supported = "/".join(s.description for s in IMAGE_SIGNATURES)
        return False, f"base64内容不是有效的图片格式({supported})"

    return True, ""
