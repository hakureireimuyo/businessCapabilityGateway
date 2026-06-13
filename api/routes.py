"""API routes — HTTP interface for Agent interaction"""

from flask import Blueprint, request, jsonify

from core.registry.node_registry import get_registry
from core.exceptions import GatewayException
from core.logger import get_logger

logger = get_logger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="")


# ================================================================
# Discovery endpoints
# ================================================================

@api_bp.route("/plugins", methods=["GET"])
def list_plugins():
    """GET /plugins — list all loaded plugin names."""
    registry = get_registry()
    plugins = registry.get_all_plugins()
    logger.info("List plugins: %s", plugins)
    return jsonify(plugins)


@api_bp.route("/plugins/<plugin_name>/nodes", methods=["GET"])
def list_plugin_nodes(plugin_name: str):
    """GET /plugins/<plugin>/nodes — lightweight summary list of all nodes.

    Returns just enough for the Agent to scan what's available:
      name, description, is_entry, input_count, output_key, output_type.

    For the full protocol spec of a specific node, request:
      GET /plugins/<plugin>/nodes/<node_name>
    """
    registry = get_registry()
    try:
        summaries = registry.list_summaries(plugin_name)
        return jsonify(summaries)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/plugins/<plugin_name>/nodes/<node_name>", methods=["GET"])
def get_node_spec(plugin_name: str, node_name: str):
    """GET /plugins/<plugin>/nodes/<node> — full protocol spec of a single node.

    Returns everything the Agent needs to wire this node into a Graph:
      input_specs (every input with artifact_type, required flag, description),
      output_spec (key, artifact_type, description),
      parameter_specs (every parameter with type, required flag, default, description).
    """
    registry = get_registry()
    try:
        spec = registry.get_spec(plugin_name, node_name)
        return jsonify(spec)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/plugins/<plugin_name>/actions", methods=["GET"])
def list_plugin_actions(plugin_name: str):
    """GET /plugins/<plugin>/actions — legacy alias, returns summaries (same as /nodes)."""
    return list_plugin_nodes(plugin_name)

@api_bp.route("/plugins/<plugin_name>/actions/<node_name>", methods=["GET"])
def get_action_spec(plugin_name: str, node_name: str):
    """GET /plugins/<plugin>/actions/<node> — legacy alias, returns full spec."""
    return get_node_spec(plugin_name, node_name)


@api_bp.route("/capabilities", methods=["GET"])
def all_capabilities():
    """GET /capabilities — list all plugins' capabilities."""
    registry = get_registry()
    return jsonify(registry.get_capabilities())


# ================================================================
# Execution endpoint
# ================================================================

@api_bp.route("/execute", methods=["POST"])
def execute_graph():
    """POST /execute — execute a Python script that builds and runs a Graph.

    Content-Type: text/plain
    Body: Python script using the Gateway SDK

    Example:
        g = Graph(plugin="amazon")
        products = g.keyword_search(keyword="halloween garland")
        analysis = g.market_analysis(products=products)
        g.output(analysis)
        result = g.execute()
    """
    from core.sandbox.sandbox_executor import execute_script, SandboxTimeoutError
    from core.sandbox.ast_validator import ASTValidationError
    from gateway_sdk.exceptions import GraphError
    from core.exceptions import GatewayException, InvalidGraphError

    raw_body = request.get_data(as_text=True)

    if not raw_body or not raw_body.strip():
        return jsonify({
            "success": False,
            "error": {
                "code": "EMPTY_REQUEST",
                "message": "Request body is empty",
            }
        }), 400

    logger.info("Execute request (%d chars)", len(raw_body))

    try:
        result_data = execute_script(raw_body)

        return jsonify({
            "success": True,
            "data": result_data,
            "message": "Graph executed",
        }), 200

    except ASTValidationError as e:
        logger.warning("AST validation error: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_SCRIPT", "message": str(e)},
        }), 400

    except SandboxTimeoutError as e:
        logger.warning("Script timeout: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "EXECUTION_TIMEOUT", "message": str(e)},
        }), 400

    except InvalidGraphError as e:
        logger.warning("Graph validation error: %s", e)
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_GRAPH",
                "message": str(e),
                "errors": e.errors,
            }
        }), 400

    except GraphError as e:
        logger.warning("SDK error: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_SCRIPT", "message": str(e)},
        }), 400

    except GatewayException as e:
        logger.error("Gateway error: [%s] %s", e.code, e.message)
        return jsonify({
            "success": False,
            "error": {"code": e.code, "message": e.message},
        }), 400

    except Exception as e:
        logger.exception("Unexpected error")
        return jsonify({
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": str(e)},
        }), 500


# ================================================================
# Health
# ================================================================

@api_bp.route("/health", methods=["GET"])
def health():
    """GET /health — health check."""
    return jsonify({"status": "ok"})
