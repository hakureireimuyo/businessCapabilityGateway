"""
Tag IR → 搜索 URL 的基类转换器。

职责：
    - expand(): Cartesian product over should groups（通用逻辑）
    - encode_query(): 模板方法，调子类的 encode_and / encode_not
    - build(): 完整流程 — expand → encode_query → build_url

子类必须重写：
    - encode_and(tags) → str   # 即使实现与基类相同也要显式重写
    - encode_not(tag) → str    # 同上
    - build_url(query) → str   # 站点特定 URL 模板
"""

import itertools
from abc import ABC, abstractmethod
from typing import List

# OR 展开结果数量上限
MAX_EXPAND = 64


class ExpandLimitError(Exception):
    """OR 展开结果数超过 MAX_EXPAND 时抛出。"""

    def __init__(self, count: int):
        self.count = count
        super().__init__(
            f"OR expansion count ({count}) exceeds limit ({MAX_EXPAND}). "
            f"Reduce the number of OR groups or elements per group."
        )


class BaseTagURLBuilder(ABC):
    """Tag IR 转换器基类。

    Tag IR 格式:
        {
            "must":   ["tag1", "tag2"],          # AND — 每条结果必须全部包含
            "should": [["a", "b"], ["c", "d"]],  # OR 组 — 组间 AND，组内 OR
            "not":    ["tag3"]                   # NOT — 全局排除
        }

    使用方式:
        builder = PixivURLBuilder()
        results = builder.build(tag_ir)
        # → [{"url": "https://...", "and": [...], "not": [...]}, ...]
    """

    # ---- expand（通用，子类不重写） ----

    def expand(
        self,
        must: List[str],
        should: List[List[str]],
        not_tags: List[str],
    ) -> List[dict]:
        """Cartesian product over should groups.

        没有 should 组时返回单条（仅 must + not）。
        展开超过 MAX_EXPAND 时抛出 ExpandLimitError。

        Returns:
            [{"and": [...], "not": [...]}, ...]
        """
        if not should:
            return [{"and": list(must), "not": list(not_tags)}]

        count = 1
        for group in should:
            count *= len(group)

        if count > MAX_EXPAND:
            raise ExpandLimitError(count)

        results: List[dict] = []
        for combo in itertools.product(*should):
            results.append({
                "and": must + list(combo),
                "not": list(not_tags),
            })
        return results

    # ---- encode_query（模板方法，子类不重写） ----

    def encode_query(self, flat: dict) -> str:
        """将单条平铺 tag 组编码为搜索字符串。

        模板方法：依次调用子类重写的 encode_and 和 encode_not。
        子类不应重写此方法——编码差异通过重写 encode_and / encode_not 注入。
        """
        parts = []
        if flat["and"]:
            parts.append(self.encode_and(flat["and"]))
        for t in flat["not"]:
            parts.append(self.encode_not(t))
        return " ".join(parts)

    # ---- 子类必须重写的方法 ----

    def encode_and(self, tags: List[str]) -> str:
        """多个 tag 如何用 AND 连接。默认空格分隔。

        子类必须显式重写此方法，即使实现与基类相同也应调用 super()。
        "显示优于隐式"——每个站点的规则在代码中可见。
        """
        return " ".join(tags)

    def encode_not(self, tag: str) -> str:
        """NOT 如何编码。默认 '-tag' 格式。

        子类必须显式重写此方法，即使实现与基类相同也应调用 super()。
        """
        return f"-{tag}"

    @abstractmethod
    def build_url(self, query: str) -> str:
        """将编码后的搜索字符串拼接为完整 URL。

        每个站点子类必须实现，包含 URL 编码处理。
        """
        ...

    # ---- build（完整流程，子类不重写） ----

    def build(self, tag_ir: dict) -> List[dict]:
        """完整流程：Tag IR → expand → encode_query → build_url。

        Args:
            tag_ir:
                {
                    "must": ["tag1", ...],
                    "should": [["a", "b"], ...],
                    "not": ["tag3", ...]
                }

        Returns:
            [
                {
                    "url": "https://...?q=tag1%20tag2",
                    "and": ["tag1", "tag2"],
                    "not": ["tag3"]
                },
                ...
            ]

        Raises:
            ExpandLimitError: should 展开超过 MAX_EXPAND
        """
        must = tag_ir.get("must", [])
        should = tag_ir.get("should", [])
        not_tags = tag_ir.get("not", [])

        flat_queries = self.expand(must, should, not_tags)

        results: List[dict] = []
        for flat in flat_queries:
            query_str = self.encode_query(flat)
            url = self.build_url(query_str)
            results.append({
                "url": url,
                "and": flat["and"],
                "not": flat["not"],
            })
        return results
