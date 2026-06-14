"""Image Search Gallery-DL Plugin — Artifact type hierarchy.

GalleryTask: 累加的参数描述符（不可变语义 — 每个节点返回新副本）
DownloadResult: download 节点产出 — 下载汇总
"""

from core.protocol.artifact import ArtifactType


class GalleryTask(ArtifactType):
    """累积的 gallery-dl 任务描述符。

    入口节点 search_url 创建实例，后续转换节点逐层叠加字段后返回新副本。
    download 节点消费该类型并在内部拼出完整的 gallery-dl 命令。
    """
    pass


class DownloadResult(ArtifactType):
    """download 节点的产出 — 下载执行汇总。

    包含总数、文件列表、各 URL 的下载统计。
    """
    pass
