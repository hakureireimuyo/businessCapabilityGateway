"""日志模块"""

import logging
import sys

# 网关日志器
gateway_logger = logging.getLogger("gateway")
gateway_logger.setLevel(logging.DEBUG)

_handler = logging.StreamHandler(sys.stdout)
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
gateway_logger.addHandler(_handler)


def get_logger(name: str = "gateway") -> logging.Logger:
    """获取日志器 — 始终返回 gateway 命名空间下的 logger，确保日志能传播到已配置的 handler。"""
    if name == "gateway":
        return logging.getLogger("gateway")
    return logging.getLogger(f"gateway.{name}")
