"""插件加载器 —— 自动发现并加载插件"""

import importlib
import os
import pkgutil
from pathlib import Path

from .logger import get_logger
from .node_registry import get_registry

logger = get_logger(__name__)

# 插件包路径（相对于项目根目录）
PLUGINS_PACKAGE = "plugins"


def discover_and_load_plugins(plugins_dir: str | None = None) -> list[str]:
    """自动发现并加载所有插件

    扫描 plugins/ 目录，加载每个包含 plugin.py 的子目录。
    插件目录中必须有 plugin.py 文件，且其中包含 register() 函数。

    Args:
        plugins_dir: 插件目录路径，默认为项目下的 plugins/

    Returns:
        成功加载的插件名列表
    """
    if plugins_dir is None:
        # 默认为 core/../plugins/
        plugins_dir = str(
            Path(__file__).resolve().parent.parent / "plugins"
        )

    if not os.path.isdir(plugins_dir):
        logger.warning("插件目录不存在: %s", plugins_dir)
        return []

    loaded_plugins: list[str] = []

    # 扫描 plugins/ 下的每个子目录
    for entry in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, entry)

        # 跳过文件、__pycache__、以 _ 或 . 开头的目录
        if not os.path.isdir(plugin_path):
            continue
        if entry.startswith("_") or entry.startswith("."):
            continue
        if entry == "__pycache__":
            continue

        # 检查是否有 plugin.py
        plugin_file = os.path.join(plugin_path, "plugin.py")
        if not os.path.isfile(plugin_file):
            logger.debug("跳过 %s: 缺少 plugin.py", entry)
            continue

        try:
            _load_plugin(entry, plugin_path)
            loaded_plugins.append(entry)
            logger.info("插件加载成功: %s", entry)
        except Exception as e:
            logger.error("插件加载失败 %s: %s", entry, e)

    return loaded_plugins


def _load_plugin(plugin_name: str, plugin_path: str) -> None:
    """加载单个插件

    动态导入 plugin.py 并调用其 register() 函数。
    """
    import sys

    # 确保项目根目录在 sys.path 中（core/../ 即项目根）
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 使用完整包路径: plugins.<plugin_name>.plugin
    full_module_name = f"plugins.{plugin_name}.plugin"

    try:
        module = importlib.import_module(full_module_name)
    except ImportError:
        # 备用方案: 从文件路径直接加载
        spec = importlib.util.spec_from_file_location(
            f"plugins_{plugin_name}_plugin",
            os.path.join(plugin_path, "plugin.py"),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载插件模块: {plugin_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugins_{plugin_name}_plugin"] = module
        spec.loader.exec_module(module)

    # 调用插件的 register() 函数
    if hasattr(module, "register"):
        module.register()
    else:
        raise AttributeError(f"插件 {plugin_name} 缺少 register() 函数")
