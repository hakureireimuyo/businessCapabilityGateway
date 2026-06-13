"""Plugin: loader — auto-discover and load plugins"""

import importlib
import importlib.util
import os
from pathlib import Path

from ..logger import get_logger

logger = get_logger(__name__)

PLUGINS_PACKAGE = "plugins"


def discover_and_load_plugins(plugins_dir: str | None = None) -> list[str]:
    """Auto-discover and load all plugin directories under plugins/.

    Each plugin directory must contain a plugin.py with a register() function.
    """
    if plugins_dir is None:
        plugins_dir = str(
            Path(__file__).resolve().parent.parent.parent / "plugins"
        )

    if not os.path.isdir(plugins_dir):
        logger.warning("Plugin directory not found: %s", plugins_dir)
        return []

    loaded_plugins: list[str] = []

    for entry in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, entry)

        if not os.path.isdir(plugin_path):
            continue
        if entry.startswith("_") or entry.startswith("."):
            continue
        if entry == "__pycache__":
            continue

        plugin_file = os.path.join(plugin_path, "plugin.py")
        if not os.path.isfile(plugin_file):
            logger.debug("Skipping %s: no plugin.py", entry)
            continue

        try:
            _load_plugin(entry, plugin_path)
            loaded_plugins.append(entry)
            logger.info("Plugin loaded: %s", entry)
        except Exception as e:
            logger.error("Plugin load failed %s: %s", entry, e)

    return loaded_plugins


def _load_plugin(plugin_name: str, plugin_path: str) -> None:
    """Dynamically import and register a single plugin."""
    import sys

    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    full_module_name = f"plugins.{plugin_name}.plugin"

    try:
        module = importlib.import_module(full_module_name)
    except ImportError:
        spec = importlib.util.spec_from_file_location(
            f"plugins_{plugin_name}_plugin",
            os.path.join(plugin_path, "plugin.py"),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin: {plugin_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugins_{plugin_name}_plugin"] = module
        spec.loader.exec_module(module)

    if hasattr(module, "register"):
        module.register()
    else:
        raise AttributeError(f"Plugin '{plugin_name}' missing register()")
