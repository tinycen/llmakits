"""
消息验证器
负责验证内容的有效性
"""

# 定义不同文件类型的base64特征
BASE64_SIGNATURES = {
    "jpeg": ("/9j/", "JPEG图片"),
    "png": ("iVBORw0KGgo", "PNG图片"),
    "gif": ("R0lGODlh", "GIF图片"),
    "html": ("PCFET0NUWVBFIGh0bWw+", "HTML文档"),
}
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
    if expected_type == "image" and base64_str.startswith(BASE64_SIGNATURES["html"][0]):
        return False, f"检测到 base64 内容为：HTML，请检查URL是否为有效的图片链接(或者文件下载失败)"

    # 如果不限制类型，直接通过
    if expected_type == "any":
        return True, ""

    # 验证是否为图片类型
    if expected_type == "image":
        image_signatures = [BASE64_SIGNATURES["jpeg"][0], BASE64_SIGNATURES["png"][0], BASE64_SIGNATURES["gif"][0]]
        for sig in image_signatures:
            if base64_str.startswith(sig):
                return True, ""
        return False, "base64内容不是有效的图片格式(JPEG/PNG/GIF)"

    return True, ""
