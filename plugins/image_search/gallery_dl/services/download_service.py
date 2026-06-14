"""Gallery-DL Plugin — download execution service.

Pure business logic.  Receives plain Python data (not Artifact) and returns dict.

Uses gallery_dl's Python API directly (no subprocess), with:
  - Thread-safe config save/restore (threading.Lock)
  - Per-URL temp directories for result counting
  - Even allocation + deficit redistribution
"""

from __future__ import annotations

import math
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..repository.gallery_config import config as fixed_config

# ---- thread-safe config wrapper ----

_config_lock = threading.Lock()
_SENTINEL = object()


class _ConfigGuard:
    """Thread-safe config context manager for gallery_dl.

    gallery_dl.config is a process-global dict.  We save/restore keys
    under a lock to prevent concurrent Node executions from clobbering
    each other.
    """

    def __init__(self):
        self._saved: dict[tuple, Any] = {}

    def set(self, path: tuple, key: str, value: Any):
        import gallery_dl
        self._saved[(path, key)] = gallery_dl.config.get(path, key, _SENTINEL)
        gallery_dl.config.set(path, key, value)

    def restore(self):
        import gallery_dl
        for (path, key), old in self._saved.items():
            if old is _SENTINEL:
                # was not previously set — best-effort removal
                try:
                    gallery_dl.config.unset(path, key)
                except Exception:
                    pass
            else:
                gallery_dl.config.set(path, key, old)


# ---- data types ----

@dataclass
class DownloadTask:
    """待执行的 gallery-dl 任务描述符（Service 层，不接触 Artifact）。"""

    urls: list[str] = field(default_factory=list)
    limit: int | None = None        # 总下载数量上限
    range: str | None = None        # gallery-dl --range
    filter_expr: str | None = None  # gallery-dl --filter
    simulate: bool = False          # gallery-dl -s


# ---- per-URL download ----

def _run_download_for_url(
    url: str,
    per_url_limit: int | None,
    task: DownloadTask,
    output_dir: str,
    *,
    simulate: bool = False,
) -> tuple[int, list[dict]]:
    """Run gallery-dl DownloadJob for a single URL.

    Returns (downloaded_count, []).

    Sets gallery-dl config to:
      - -d output_dir        (flat directory for easy counting)
      - -f "{id}_{num}.{extension}"
      - --limit per_url_limit   (None = unlimited)
      - --range / --filter     (if set in task)
      - fixed config values    (sleep, retries, archive, cookies, etc.)
      - -j (always on)

    Thread-safe: uses _ConfigGuard + _config_lock.
    """
    import gallery_dl
    from gallery_dl import job

    guard = _ConfigGuard()

    with _config_lock:
        # ---- output ----
        guard.set((), "base-directory", output_dir)
        guard.set((), "directory", ())                     # no subdirs = flat
        guard.set((), "filename", fixed_config.filename_template)

        # ---- metadata ----
        guard.set((), "write-metadata", fixed_config.write_metadata)
        guard.set((), "write-tags", fixed_config.write_tags)

        # ---- throttle ----
        if fixed_config.sleep_request:
            guard.set((), "sleep-request", fixed_config.sleep_request)

        # ---- retry ----
        guard.set(("extractor",), "retries", fixed_config.extractor_retries)
        if fixed_config.retry_codes:
            guard.set(("extractor",), "retry-codes",
                      _parse_retry_codes(fixed_config.retry_codes))

        # ---- archive (dedup) ----
        if fixed_config.archive_path:
            os.makedirs(os.path.dirname(fixed_config.archive_path), exist_ok=True)
            guard.set(("extractor",), "archive", fixed_config.archive_path)

        # ---- cookies ----
        if fixed_config.cookies_from_browser:
            browser, sep, profile = fixed_config.cookies_from_browser.partition(":")
            guard.set((), "cookies", (browser, profile or None, None, None, None))
        elif fixed_config.cookies_file:
            guard.set((), "cookies-file", fixed_config.cookies_file)

        # ---- per-request params ----
        if per_url_limit is not None:
            guard.set((), "limit", per_url_limit)
        if task.range:
            guard.set((), "range", task.range)
        if task.filter_expr:
            guard.set((), "filter", task.filter_expr)

        # ---- execute ----
        try:
            j = job.DownloadJob(url)
            status = j.run()
            # status == 0  means success
            # status & 4 means individual file download failures
            # status & 128 means OS error
        finally:
            guard.restore()

    # ---- count downloaded files ----
    downloaded = _count_files(output_dir)

    return downloaded, []


def _count_files(directory: str) -> int:
    """Count non-metadata files in a directory.

    Excludes .json and .txt sidecar files (--write-metadata / --write-tags).
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return 0
    count = 0
    for entry in dir_path.iterdir():
        if entry.is_file() and entry.suffix.lower() not in (".json", ".txt"):
            count += 1
    return count


def _parse_retry_codes(raw: str) -> list[int]:
    """Parse "[429, 503]" into [429, 503]."""
    try:
        import ast
        return ast.literal_eval(raw)
    except Exception:
        return []


# ---- allocation + orchestration ----

def execute_download(task: DownloadTask) -> dict[str, Any]:
    """Execute download with even allocation + deficit redistribution.

    Algorithm:
      1. Initial allocation: even split of total_limit across URLs
         - base = limit // url_count
         - remainder URLs (first N) get +1
      2. Each URL runs in its own temp directory (for accurate counting)
      3. After each URL: count downloaded files
         - If actual < allocated → exhausted → deficit redistributed to next URL
         - If actual >= allocated or total reached → done
      4. Files moved from temp dirs to final output dir after all URLs complete

    Returns:
        {
            "total_downloaded": int,
            "total_limit": int | None,
            "url_stats": [{
                "url": str,
                "allocated": int,
                "downloaded": int,
                "exhausted": bool,
                "skipped": bool,
            }, ...],
        }
    """
    urls = task.urls
    total_limit = task.limit

    if not urls:
        return {
            "total_downloaded": 0,
            "total_limit": total_limit,
            "url_stats": [],
        }

    url_count = len(urls)

    # ---- initial allocation ----
    if total_limit is not None:
        base = total_limit // url_count
        remainder = total_limit % url_count
        allocations = [base + (1 if i < remainder else 0) for i in range(url_count)]
    else:
        allocations = [None] * url_count

    total_downloaded = 0
    surplus = 0
    url_stats: list[dict] = []
    temp_dirs: list[str] = []

    for i, url in enumerate(urls):
        # ---- check early stop ----
        if total_limit is not None and total_downloaded >= total_limit:
            for j in range(i, url_count):
                url_stats.append({
                    "url": urls[j],
                    "allocated": allocations[j],
                    "downloaded": 0,
                    "exhausted": False,
                    "skipped": True,
                })
            break

        # ---- calculate this URL's allocation ----
        allocated = allocations[i]

        # redistribute surplus
        if total_limit is not None and surplus > 0:
            if allocated is None:
                allocated = surplus
            else:
                allocated += surplus
            surplus = 0

        # skip zero-allocation URLs
        if allocated is not None and allocated <= 0:
            url_stats.append({
                "url": url,
                "allocated": 0,
                "downloaded": 0,
                "exhausted": False,
                "skipped": True,
            })
            continue

        # ---- execute download ----
        temp_dir = tempfile.mkdtemp(prefix=f"gallerydl_{i}_")
        temp_dirs.append(temp_dir)

        try:
            actual, _ = _run_download_for_url(
                url=url,
                per_url_limit=allocated,
                task=task,
                output_dir=temp_dir,
                simulate=task.simulate,
            )
        except Exception as exc:
            url_stats.append({
                "url": url,
                "allocated": allocated,
                "downloaded": 0,
                "exhausted": False,
                "error": str(exc),
            })
            continue

        total_downloaded += actual
        exhausted = (allocated is not None and actual < allocated)

        if exhausted and total_limit is not None and allocated is not None:
            deficit = allocated - actual
            surplus += deficit

        url_stats.append({
            "url": url,
            "allocated": allocated,
            "downloaded": actual,
            "exhausted": exhausted,
        })

    # ---- move files to final output dir ----
    final_dir = fixed_config.output_dir
    os.makedirs(final_dir, exist_ok=True)
    for temp_dir in temp_dirs:
        if not os.path.isdir(temp_dir):
            continue
        for entry in os.listdir(temp_dir):
            src = os.path.join(temp_dir, entry)
            dst = os.path.join(final_dir, entry)
            if os.path.isfile(src):
                # avoid overwriting; rename if conflicts (rare in practice)
                if os.path.exists(dst):
                    base, ext = os.path.splitext(entry)
                    counter = 1
                    while os.path.exists(dst):
                        dst = os.path.join(final_dir, f"{base}_{counter}{ext}")
                        counter += 1
                shutil.move(src, dst)
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    return {
        "total_downloaded": total_downloaded,
        "total_limit": total_limit,
        "url_stats": url_stats,
    }
