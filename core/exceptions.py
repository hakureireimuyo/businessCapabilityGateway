"""Gateway exceptions — graph-era protocol errors"""


class GatewayException(Exception):
    """Base gateway exception with error code."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class PluginNotFoundException(GatewayException):
    def __init__(self, plugin_name: str):
        super().__init__("PLUGIN_NOT_FOUND", f"Plugin '{plugin_name}' not found")


class NodeNotFoundException(GatewayException):
    def __init__(self, plugin_name: str, node_name: str):
        super().__init__(
            "NODE_NOT_FOUND",
            f"Node '{node_name}' not found in plugin '{plugin_name}'",
        )


class TypeMismatchError(GatewayException):
    def __init__(self, message: str):
        super().__init__("TYPE_MISMATCH", message)


class CyclicDependencyError(GatewayException):
    def __init__(self, message: str = "Graph contains a cyclic dependency"):
        super().__init__("CYCLIC_DEPENDENCY", message)


class UnsatisfiedInputError(GatewayException):
    def __init__(self, node_id: str, input_name: str):
        super().__init__(
            "UNSATISFIED_INPUT",
            f"Node '{node_id}' has unsatisfied required input '{input_name}'",
        )


class InvalidParamsError(GatewayException):
    def __init__(self, message: str):
        super().__init__("INVALID_PARAMS", message)


class CrossPluginError(GatewayException):
    def __init__(self):
        super().__init__(
            "CROSS_PLUGIN",
            "Cross-plugin references are not allowed",
        )


class DanglingOutputError(GatewayException):
    def __init__(self, node_id: str):
        super().__init__(
            "DANGLING_OUTPUT",
            f"Output references unknown node '{node_id}'",
        )


class ExecutionFailedError(GatewayException):
    def __init__(self, node_id: str, message: str):
        super().__init__(
            "EXECUTION_FAILED",
            f"Node '{node_id}' failed: {message}",
        )


class DeadlockError(GatewayException):
    def __init__(self, message: str = "Deadlock: unsatisfiable dependencies"):
        super().__init__("DEADLOCK", message)


class EmptyGraphError(GatewayException):
    def __init__(self):
        super().__init__("EMPTY_GRAPH", "Graph has no nodes")


class InvalidGraphError(GatewayException):
    """Aggregated validation error carrying all individual errors."""
    def __init__(self, errors: list[dict]):
        self.errors = errors
        detail = "; ".join(
            e.get("message", str(e)) for e in errors[:3]
        )
        if len(errors) > 3:
            detail += f" ... and {len(errors) - 3} more"
        super().__init__("INVALID_GRAPH", detail)
