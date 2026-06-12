"""管道执行器 —— 校验并顺序执行管道节点"""

import time
from typing import Any

from .execution_context import ExecutionContext
from .dsl_parser import Pipeline as ParsedPipeline
from .node_registry import get_registry
from .node import NodeType
from .response import ActionResult
from .exceptions import (
    InvalidPipelineException,
    InvalidParamsException,
    GatewayException,
)
from .logger import get_logger

logger = get_logger(__name__)

# 最大返回结果大小（字节数）
MAX_RESULT_SIZE = 10 * 1024 * 1024  # 10 MB


class PipelineExecutor:
    """管道执行器：校验管道合法性并顺序执行节点"""

    def __init__(self, max_result_size: int = MAX_RESULT_SIZE):
        self.max_result_size = max_result_size
        self.registry = get_registry()

    def execute(self, pipeline: ParsedPipeline) -> ActionResult:
        """执行完整管道并返回结果

        Args:
            pipeline: 解析后的 Pipeline 对象

        Returns:
            ActionResult: 统一执行结果
        """
        start_time = time.time()
        node_names = [n.name for n in pipeline.nodes]

        logger.info(
            "执行管道: %s -> %s",
            pipeline.plugin,
            " > ".join(node_names),
        )

        try:
            # 1. 校验管道结构
            errors = self.registry.validate_pipeline_nodes(
                pipeline.plugin, node_names
            )
            if errors:
                raise InvalidPipelineException("; ".join(errors))

            # 2. 校验每个节点的参数
            for pipe_node in pipeline.nodes:
                node = self.registry.get_node(pipeline.plugin, pipe_node.name)
                param_errors = node.validate_params(pipe_node.params)
                if param_errors:
                    raise InvalidParamsException(
                        f"节点 '{pipe_node.name}': {'; '.join(param_errors)}"
                    )

            # 3. 顺序执行节点
            context = ExecutionContext(
                plugin_name=pipeline.plugin,
                pipeline_nodes=[
                    {"name": n.name, "params": n.params}
                    for n in pipeline.nodes
                ],
            )

            for pipe_node in pipeline.nodes:
                node = self.registry.get_node(pipeline.plugin, pipe_node.name)
                context.set_current_params(pipe_node.params)

                logger.debug("执行节点: %s.%s", pipeline.plugin, pipe_node.name)
                node_start = time.time()

                context = node.execute(context)

                node_elapsed = (time.time() - node_start) * 1000
                logger.debug(
                    "节点完成: %s.%s (%.1fms)",
                    pipeline.plugin, pipe_node.name, node_elapsed,
                )

            # 4. 提取结果
            result_data = context.result if context.result else {}
            total_elapsed = (time.time() - start_time) * 1000

            logger.info(
                "管道执行完成: request_id=%s, 耗时=%.1fms",
                context.request_id, total_elapsed,
            )

            return ActionResult.ok(
                data=result_data,
                message=f"执行成功 ({total_elapsed:.0f}ms)",
            )

        except GatewayException:
            raise
        except Exception as e:
            logger.exception("管道执行异常")
            return ActionResult.fail("INTERNAL_ERROR", str(e))
