"""Amazon 插件 —— 入口"""

from core.node_registry import register_nodes
from plugins.amazon.nodes.source_nodes import KeywordSearchNode, CategorySearchNode
from plugins.amazon.nodes.transform_nodes import FilterNode, SortNode
from plugins.amazon.nodes.sink_nodes import (
    MarketAnalysisNode,
    OpportunityAnalysisNode,
    CompetitionAnalysisNode,
)


def register():
    """向网关注册 Amazon 插件的所有 Node"""
    register_nodes("amazon", [
        # Source
        KeywordSearchNode(),
        CategorySearchNode(),
        # Transform
        FilterNode(),
        SortNode(),
        # Sink
        MarketAnalysisNode(),
        OpportunityAnalysisNode(),
        CompetitionAnalysisNode(),
    ])
