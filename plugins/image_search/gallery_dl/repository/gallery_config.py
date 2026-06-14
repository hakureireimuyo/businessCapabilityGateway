"""Gallery-DL Plugin — 固定配置。

这些参数不进 Graph 编排，由 download 节点执行时直接读取。
Agent 不需要关心这些值 — 它们在项目约定的层面上保持一致。
"""

from pathlib import Path


class GalleryConfig:
    """项目级 gallery-dl 固定参数。

    实例属性集中管理，download 节点在执行时合并进生成的 gallery-dl 命令。
    """

    # ---- 输出 ----
    output_dir: str = str(Path("downloads").resolve())          # -d
    filename_template: str = "{id}_{num}.{extension}"           # -f

    # ---- 元数据（始终开启） ----
    write_metadata: bool = True                                 # --write-metadata
    write_tags: bool = True                                     # --write-tags
    json_output: bool = True                                    # -j（JSON stdout）

    # ---- 反爬 / 节流 ----
    sleep_request: float = 2.0                                  # --sleep-request

    # ---- 重试 ----
    extractor_retries: int = 10                                 # -o extractor.retries=
    retry_codes: str = "[429, 503]"                             # -o extractor.retry-codes=

    # ---- 去重 ----
    archive_path: str = str(Path("downloads") / "archive.db")   # -o extractor.archive=

    # ---- 认证 ----
    cookies_from_browser: str | None = None                     # --cookies-from-browser
    cookies_file: str | None = None                             # --cookies


# 单例
config = GalleryConfig()
