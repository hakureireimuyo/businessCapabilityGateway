"""API 路由定义"""

import json
from flask import Blueprint, request, jsonify

from core.dsl_parser import parse_bcl
from core.pipeline_executor import PipelineExecutor
from core.node_registry import get_registry
from core.exceptions import GatewayException
from core.logger import get_logger

logger = get_logger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="")


@api_bp.route("/plugins", methods=["GET"])
def list_plugins():
    """GET /plugins —— 列出所有已加载的插件名"""
    registry = get_registry()
    plugins = registry.get_all_plugins()
    logger.info("列出插件: %s", plugins)
    return jsonify(plugins)


@api_bp.route("/plugins/<plugin_name>/actions", methods=["GET"])
def list_plugin_actions(plugin_name: str):
    """GET /plugins/<plugin>/actions —— 列出插件的能力/节点"""
    registry = get_registry()
    try:
        capabilities = registry.get_capabilities(plugin_name)
        return jsonify(capabilities["actions"])
    except Exception:
        return jsonify({"error": f"插件 '{plugin_name}' 未找到"}), 404


@api_bp.route("/capabilities", methods=["GET"])
def all_capabilities():
    """GET /capabilities —— 列出所有插件的能力"""
    registry = get_registry()
    return jsonify(registry.get_capabilities())


@api_bp.route("/execute", methods=["POST"])
def execute_pipeline():
    """POST /execute —— 执行 BCL 管道指令

    Content-Type: text/plain
    Body: BCL 指令字符串
    """
    bcl_string = request.get_data(as_text=True)

    if not bcl_string or not bcl_string.strip():
        return jsonify({
            "success": False,
            "error": {
                "code": "EMPTY_REQUEST",
                "message": "请求体不能为空"
            }
        }), 400

    logger.info("收到执行请求:\n%s", bcl_string)

    try:
        # 1. 解析 DSL
        pipeline = parse_bcl(bcl_string)

        # 2. 执行管道
        executor = PipelineExecutor()
        result = executor.execute(pipeline)

        # 3. 返回
        return jsonify(result.to_dict()), 200 if result.success else 400

    except GatewayException as e:
        logger.error("网关异常: [%s] %s", e.code, e.message)
        return jsonify({
            "success": False,
            "error": {
                "code": e.code,
                "message": e.message,
            }
        }), 400
    except Exception as e:
        logger.exception("未预期异常")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e),
            }
        }), 500


@api_bp.route("/health", methods=["GET"])
def health():
    """GET /health —— 健康检查"""
    return jsonify({"status": "ok"})
