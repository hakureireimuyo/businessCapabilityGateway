"""
Danbooru 搜索 URL 构建器。

规则:
    - AND: 空格分隔
    - NOT: -tag 前缀
    - URL 模板: https://danbooru.donmai.us/posts?tags={encoded_query}
"""

from urllib.parse import quote
from typing import List

from .base import BaseTagURLBuilder


class DanbooruURLBuilder(BaseTagURLBuilder):
    """Danbooru 站点 URL 构建器。"""

    def encode_and(self, tags: List[str]) -> str:
        """AND = 空格分隔。"""
        return super().encode_and(tags)

    def encode_not(self, tag: str) -> str:
        """NOT = '-tag' 前缀。"""
        return super().encode_not(tag)

    def build_url(self, query: str) -> str:
        """拼接 Danbooru 搜索 URL，对 query 做 URL 编码。"""
        encoded = quote(query, safe="")
        return f"https://danbooru.donmai.us/posts?tags={encoded}"
