"""
图片Base64缓存管理器
使用LRU策略缓存最多10张图片的base64编码，并记录失败URL避免重复下载
"""

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple


class ImageBase64Cache:
    """
    图片Base64缓存管理器
    使用LRU（最近最少使用）策略管理缓存
    """

    def __init__(self, max_size: int = 10):
        """
        初始化缓存

        Args:
            max_size: 最大缓存数量，默认10张图片
        """
        self.max_size = max_size
        self.cache = OrderedDict()  # 使用OrderedDict实现LRU
        self.failed_cache = OrderedDict()
        self.group_cache = OrderedDict()

    def get(self, url: str) -> Optional[str]:
        """
        从缓存中获取base64字符串

        Args:
            url: 图片URL

        Returns:
            base64字符串，如果不存在则返回None
        """
        if url not in self.cache:
            return None

        # 移动到末尾（标记为最近使用）
        self.cache.move_to_end(url)
        return self.cache[url]

    def put(self, url: str, base64_str: str) -> None:
        """
        将图片base64存入缓存

        Args:
            url: 图片URL
            base64_str: base64编码字符串
        """
        if url in self.cache:
            # 如果已存在，移动到末尾
            self.cache.move_to_end(url)
            self.cache[url] = base64_str
        else:
            # 新增条目
            self.cache[url] = base64_str
            # 如果超过容量，删除最旧的条目
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
        self.failed_cache.pop(url, None)

    def mark_failed(self, url: str, reason: str = "") -> None:
        """
        记录转换失败的图片URL。

        Args:
            url: 图片URL
            reason: 失败原因
        """
        if not url:
            return

        if url in self.failed_cache:
            self.failed_cache.move_to_end(url)
        self.failed_cache[url] = reason
        if len(self.failed_cache) > self.max_size:
            self.failed_cache.popitem(last=False)

    def is_failed(self, url: str) -> bool:
        """检查URL是否已记录为失败。"""
        if url not in self.failed_cache:
            return False
        self.failed_cache.move_to_end(url)
        return True

    def get_failed_reason(self, url: str) -> str:
        """获取失败缓存中的失败原因。"""
        if url not in self.failed_cache:
            return ""
        self.failed_cache.move_to_end(url)
        return self.failed_cache[url]

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.failed_cache.clear()
        self.group_cache.clear()

    def size(self) -> int:
        """返回当前缓存大小"""
        return len(self.cache)

    def contains(self, url: str) -> bool:
        """检查URL是否在缓存中"""
        return url in self.cache

    def failed_size(self) -> int:
        """返回当前失败缓存大小"""
        return len(self.failed_cache)

    def _make_group_key(self, img_list: List[str]) -> Tuple[str, ...]:
        """生成图片组稳定key。"""
        return tuple(img.strip() if isinstance(img, str) else str(img) for img in img_list)

    def get_group_result(self, img_list: List[str]) -> Optional[Dict[str, Any]]:
        """获取图片组处理结果。"""
        key = self._make_group_key(img_list)
        if key not in self.group_cache:
            return None
        self.group_cache.move_to_end(key)
        result = self.group_cache[key]
        return {
            "successful_images": list(result.get("successful_images", [])),
            "failed_urls": list(result.get("failed_urls", [])),
            "all_failed": bool(result.get("all_failed", False)),
        }

    def put_group_result(
        self,
        img_list: List[str],
        successful_images: List[str],
        failed_urls: List[str],
        all_failed: bool,
    ) -> None:
        """记录图片组处理结果。"""
        if not img_list:
            return

        key = self._make_group_key(img_list)
        if key in self.group_cache:
            self.group_cache.move_to_end(key)

        self.group_cache[key] = {
            "successful_images": list(successful_images),
            "failed_urls": list(failed_urls),
            "all_failed": all_failed,
        }
        if len(self.group_cache) > self.max_size:
            self.group_cache.popitem(last=False)

    def group_size(self) -> int:
        """返回当前图片组缓存大小。"""
        return len(self.group_cache)
