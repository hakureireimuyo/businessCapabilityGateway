"""Node 基类 —— 插件暴露给网关的唯一抽象"""

from abc import ABC, abstractmethod
from typing import Any

from .execution_context import ExecutionContext


class NodeType:
    """节点类型常量"""
    SOURCE = "source"        # 产生数据集合
    TRANSFORM = "transform"  # 修改数据集合
    SINK = "sink"            # 输出最终结果


class Node(ABC):
    """插件暴露给网关的唯一抽象单元

    每个 Node 必须声明：
    - name: 业务名称（如 "关键词搜索"）
    - description: 业务说明
    - node_type: source | transform | sink
    - parameters: 参数 schema
    - input_schema: 输入类型（可选）
    - output_schema: 输出 schema
    """

    name: str = ""
    description: str = ""
    node_type: str = ""
    parameters: dict[str, dict] = {}     # {param_name: {type, required, default, ...}}
    input_schema: dict | None = None     # {"type": "ProductCollection"} 或 None
    output_schema: dict | None = None    # {"type": "ProductCollection"} 或 {field: type}

    @abstractmethod
    def execute(self, context: ExecutionContext) -> ExecutionContext:
        """执行节点逻辑，返回更新后的上下文"""
        ...

    def validate_params(self, params: dict) -> list[str]:
        """校验参数，返回错误信息列表"""
        errors: list[str] = []
        for key, schema in self.parameters.items():
            if schema.get("required", False) and key not in params:
                errors.append(f"缺少必填参数: {key}")
            if key in params:
                expected_type = schema.get("type", "string")
                value = params[key]
                if expected_type == "integer":
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        errors.append(f"参数 {key} 需要整数类型")
                elif expected_type == "float":
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        errors.append(f"参数 {key} 需要浮点数类型")
        return errors

    def to_capability_dict(self) -> dict:
        """生成能力发现接口所需的描述"""
        cap: dict[str, Any] = {
            "name": self.name,
            "type": self.node_type,
            "description": self.description,
            "parameters": self.parameters,
        }
        if self.input_schema:
            cap["input"] = self.input_schema.get("type", "")
        if self.output_schema:
            cap["output_schema"] = self.output_schema
        return cap
