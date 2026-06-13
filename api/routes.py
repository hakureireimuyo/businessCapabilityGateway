"""API routes — HTTP interface for Agent interaction"""

import json
import time
from flask import Blueprint, request, jsonify

from core.graph.model import Graph
from core.graph.validator import GraphValidator
from core.graph.executor import GraphExecutor
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
    """GET /plugins/<plugin>/nodes — list node specs for a plugin.

    Returns the protocol specification for each registered node:
      - name, description
      - input_specs (what Artifacts it consumes)
      - output_spec (what Artifact it produces)
      - parameter_specs (what literal parameters it accepts)
    """
    registry = get_registry()
    try:
        specs = registry.list_specs(plugin_name)
        return jsonify(specs)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/plugins/<plugin_name>/actions", methods=["GET"])
def list_plugin_actions(plugin_name: str):
    """GET /plugins/<plugin>/actions — legacy alias, redirects to /nodes."""
    return list_plugin_nodes(plugin_name)


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
    """POST /execute — execute a graph.

    Content-Type: application/json
    Body: JSON Graph description

    Example:
    {
      "plugin": "amazon",
      "nodes": {
        "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween"}},
        "a1": {"node_name": "market_analysis", "params": {}}
      },
      "edges": [
        {"from": "s1", "from_output": "products", "to": "a1", "to_input": "products"}
      ],
      "outputs": ["a1"]
    }
    """
    raw_body = request.get_data(as_text=True)

    if not raw_body or not raw_body.strip():
        return jsonify({
            "success": False,
            "error": {
                "code": "EMPTY_REQUEST",
                "message": "Request body is empty",
            }
        }), 400

    logger.info("Execute request: %s", raw_body[:200])

    try:
        # Parse JSON body
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as e:
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_JSON",
                    "message": f"Invalid JSON: {e}",
                }
            }), 400

        # Build graph from JSON
        graph = Graph.from_dict(body)

        # Validate
        validator = GraphValidator()
        errors = validator.validate(graph)
        if errors:
            return jsonify({
                "success": False,
                "error": {
                    "code": "INVALID_GRAPH",
                    "message": f"Graph validation failed: {len(errors)} error(s)",
                    "errors": errors,
                }
            }), 400

        # Execute
        executor = GraphExecutor()
        result_data = executor.execute(graph)

        return jsonify({
            "success": True,
            "data": result_data,
            "message": f"Graph executed ({graph.node_count()} nodes)",
        }), 200

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
