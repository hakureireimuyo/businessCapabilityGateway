"""执行上下文 —— 管道节点间传递的唯一数据载体"""

import uuid
from datetime import datetime, timezone
from typing import Any


class ExecutionContext:
    """执行上下文：仅存在于内存，永远不暴露给 Agent"""

    def __init__(
        self,
        plugin_name: str = "",
        pipeline_nodes: list | None = None,
    ):
        self.request_id: str = uuid.uuid4().hex[:12]
        self.plugin_name: str = plugin_name
        self.pipeline_nodes: list = pipeline_nodes or []
        self.current_node_index: int = 0
        self.current_params: dict = {}
        self.data: Any = None          # 中间数据集（ProductCollection 等）
        self.result: dict | None = None  # 最终结果（仅 SinkNode 设置）
        self.metadata: dict = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "rows_processed": 0,
        }

    @property
    def current_node_name(self) -> str:
        if self.current_node_index < len(self.pipeline_nodes):
            return self.pipeline_nodes[self.current_node_index]["name"]
        return ""

    def advance_node(self) -> bool:
        """前进到下一个节点，返回 False 表示已无下一个"""
        self.current_node_index += 1
        return self.current_node_index < len(self.pipeline_nodes)

    def set_current_params(self, params: dict):
        self.current_params = params
