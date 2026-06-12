"""API 服务启动与关闭"""

import os
import sys
import signal
import tempfile
from pathlib import Path

from flask import Flask

from core.logger import get_logger

logger = get_logger(__name__)

# PID 文件路径（用于 stop 指令）
PID_FILE = str(Path(__file__).resolve().parent.parent / ".gateway.pid")


def create_app() -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)

    # 注册路由
    from api.routes import api_bp
    app.register_blueprint(api_bp)

    # 禁用 Flask 默认日志中的请求信息（我们用自定义日志）
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    return app


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """启动网关服务"""
    # 写 PID 文件
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))

    logger.info("========================================")
    logger.info(" 业务能力网关 (Business Capability Gateway)")
    logger.info("========================================")
    logger.info(" 监听地址: http://%s:%d", host, port)
    logger.info(" PID: %d", pid)
    logger.info(" PID 文件: %s", PID_FILE)
    logger.info("")
    logger.info(" 接口列表:")
    logger.info("   GET  /health          健康检查")
    logger.info("   GET  /plugins          列出插件")
    logger.info("   GET  /plugins/<p>/actions  查看插件能力")
    logger.info("   GET  /capabilities     查看所有能力")
    logger.info("   POST /execute          执行 BCL 管道")
    logger.info("")
    logger.info(" 按 Ctrl+C 停止服务")
    logger.info("========================================")

    app = create_app()
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        _cleanup()


def stop_server() -> bool:
    """停止网关服务

    读取 PID 文件并发送终止信号。
    返回 True 表示成功停止，False 表示未找到运行中的服务。
    """
    if not os.path.exists(PID_FILE):
        print("未找到运行中的网关服务（PID 文件不存在）")
        return False

    try:
        with open(PID_FILE, "r") as f:
            pid_str = f.read().strip()
        pid = int(pid_str)
    except (ValueError, FileNotFoundError):
        print("PID 文件无效")
        _cleanup()
        return False

    # 尝试终止进程
    try:
        if sys.platform == "win32":
            os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
        print(f"已向 PID {pid} 发送终止信号")
        _cleanup()
        return True
    except OSError:
        print(f"进程 {pid} 不存在或已停止")
        _cleanup()
        return True
    except Exception as e:
        print(f"停止服务失败: {e}")
        return False


def _cleanup():
    """清理 PID 文件"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except OSError:
        pass
