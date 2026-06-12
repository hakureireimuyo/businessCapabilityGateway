"""网关自定义异常"""


class GatewayException(Exception):
    """网关基础异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidDSLException(GatewayException):
    """DSL 语法错误"""
    def __init__(self, message: str):
        super().__init__("INVALID_DSL", message)


class PluginNotFoundException(GatewayException):
    """插件不存在"""
    def __init__(self, plugin_name: str):
        super().__init__("PLUGIN_NOT_FOUND", f"插件 '{plugin_name}' 未找到")


class NodeNotFoundException(GatewayException):
    """节点不存在"""
    def __init__(self, plugin_name: str, node_name: str):
        super().__init__(
            "NODE_NOT_FOUND",
            f"节点 '{node_name}' 在插件 '{plugin_name}' 中未找到"
        )


class InvalidParamsException(GatewayException):
    """参数校验失败"""
    def __init__(self, message: str):
        super().__init__("INVALID_PARAMS", message)


class InvalidPipelineException(GatewayException):
    """管道结构非法"""
    def __init__(self, message: str):
        super().__init__("INVALID_PIPELINE", message)


class ResultTooLargeException(GatewayException):
    """返回结果超大"""
    def __init__(self):
        super().__init__("RESULT_TOO_LARGE", "返回结果超过最大限制")


class ExecutionTimeoutException(GatewayException):
    """执行超时"""
    def __init__(self):
        super().__init__("EXECUTION_TIMEOUT", "管道执行超时")
