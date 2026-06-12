"""Node 注册中心 —— 管理所有已注册的业务节点"""

from typing import Any

from .node import Node, NodeType
from .exceptions import NodeNotFoundException, PluginNotFoundException
from .logger import get_logger

logger = get_logger(__name__)


class NodeRegistry:
    """全局节点注册中心

    结构: {plugin_name: {node_name: Node}}
    """

    def __init__(self):
        self._nodes: dict[str, dict[str, Node]] = {}

    def register(self, plugin_name: str, nodes: list[Node]) -> None:
        """为一个插件注册一组节点"""
        if plugin_name not in self._nodes:
            self._nodes[plugin_name] = {}
        for node in nodes:
            self._nodes[plugin_name][node.name] = node
            logger.info(
                "注册节点: %s/%s [%s]",
                plugin_name, node.name, node.node_type
            )

    def unregister_plugin(self, plugin_name: str) -> None:
        """注销一个插件的所有节点"""
        self._nodes.pop(plugin_name, None)
        logger.info("注销插件: %s", plugin_name)

    def get_node(self, plugin_name: str, node_name: str) -> Node:
        """获取指定节点"""
        plugin_nodes = self._nodes.get(plugin_name)
        if not plugin_nodes:
            raise PluginNotFoundException(plugin_name)
        node = plugin_nodes.get(node_name)
        if not node:
            raise NodeNotFoundException(plugin_name, node_name)
        return node

    def get_plugin_nodes(self, plugin_name: str) -> list[Node]:
        """获取某插件的所有节点"""
        plugin_nodes = self._nodes.get(plugin_name, {})
        return list(plugin_nodes.values())

    def get_all_plugins(self) -> list[str]:
        """获取所有已注册的插件名"""
        return list(self._nodes.keys())

    def get_capabilities(self, plugin_name: str | None = None) -> dict:
        """生成能力发现响应

        Args:
            plugin_name: 插件名，为 None 则返回所有插件的能力

        Returns:
            能力描述字典
        """
        if plugin_name:
            return self._get_plugin_capabilities(plugin_name)

        result: dict[str, Any] = {}
        for name in self._nodes:
            result[name] = self._get_plugin_capabilities(name)
        return result

    def _get_plugin_capabilities(self, plugin_name: str) -> dict:
        nodes = self._nodes.get(plugin_name, {})
        return {
            "plugin": plugin_name,
            "actions": [node.to_capability_dict() for node in nodes.values()],
        }

    def validate_pipeline_nodes(
        self, plugin_name: str, node_names: list[str]
    ) -> list[str]:
        """校验管道节点链的类型合法性 (Source → Transform → Sink)

        Returns:
            错误信息列表，空列表表示合法
        """
        errors: list[str] = []
        if not node_names:
            errors.append("管道至少需要一个节点")
            return errors

        node_types: list[str] = []
        for i, name in enumerate(node_names):
            node = self.get_node(plugin_name, name)
            node_types.append(node.node_type)

        # 第一个必须是 Source
        if node_types[0] != NodeType.SOURCE:
            errors.append(
                f"管道第一个节点必须是 Source 类型，"
                f"但 '{node_names[0]}' 是 {node_types[0]} 类型"
            )

        # 最后一个必须是 Sink
        if node_types[-1] != NodeType.SINK:
            errors.append(
                f"管道最后一个节点必须是 Sink 类型，"
                f"但 '{node_names[-1]}' 是 {node_types[-1]} 类型"
            )

        # 中间必须是 Transform
        for i in range(1, len(node_types) - 1):
            if node_types[i] != NodeType.TRANSFORM:
                errors.append(
                    f"管道中间节点必须是 Transform 类型，"
                    f"但 '{node_names[i]}' 是 {node_types[i]} 类型"
                )

        # 检查是否有 Sink 后面还有节点
        for i, t in enumerate(node_types):
            if t == NodeType.SINK and i < len(node_types) - 1:
                errors.append(
                    f"Sink 节点 '{node_names[i]}' 后不能跟随其他节点"
                )
                break

        return errors


# 全局单例
_registry: NodeRegistry | None = None


def get_registry() -> NodeRegistry:
    """获取全局节点注册中心"""
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
    return _registry


def register_nodes(plugin_name: str, nodes: list[Node]) -> None:
    """便捷函数：向全局注册中心注册节点"""
    get_registry().register(plugin_name, nodes)
