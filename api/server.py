"""API server — start, stop, status"""

import os
import sys
import signal
from pathlib import Path

from flask import Flask

from core.logger import get_logger

logger = get_logger(__name__)

PID_FILE = str(Path(__file__).resolve().parent.parent / ".gateway.pid")


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    from api.routes import api_bp
    app.register_blueprint(api_bp)

    # Suppress Flask's default request logging
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    return app


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the gateway server."""
    # Write PID file
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))

    logger.info("=" * 48)
    logger.info(" Business Capability Gateway v2.0")
    logger.info(" Protocol: Node + Graph (DAG)")
    logger.info("=" * 48)
    logger.info(" Listen: http://%s:%d", host, port)
    logger.info(" PID: %d (%s)", pid, PID_FILE)
    logger.info("")
    logger.info(" Endpoints:")
    logger.info("   GET  /health                     health check")
    logger.info("   GET  /plugins                     list plugins")
    logger.info("   GET  /plugins/<name>/nodes        node spec discovery")
    logger.info("   POST /execute                     execute graph (JSON)")
    logger.info("=" * 48)

    app = create_app()
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        _cleanup()


def stop_server() -> bool:
    """Stop a running gateway server by PID.

    Returns:
        True if stopped successfully or already stopped.
    """
    if not os.path.exists(PID_FILE):
        print("No running gateway found (PID file missing)")
        return False

    try:
        with open(PID_FILE, "r") as f:
            pid_str = f.read().strip()
        pid = int(pid_str)
    except (ValueError, FileNotFoundError):
        print("PID file is invalid")
        _cleanup()
        return False

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent termination signal to PID {pid}")
        _cleanup()
        return True
    except OSError:
        print(f"Process {pid} not found — already stopped")
        _cleanup()
        return True
    except Exception as e:
        print(f"Failed to stop: {e}")
        return False


def _cleanup():
    """Remove PID file."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except OSError:
        pass
