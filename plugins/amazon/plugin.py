"""Amazon plugin — entry point"""

from core.registry.node_registry import register_nodes
from plugins.amazon.nodes.source_nodes import KeywordSearchNode, CategorySearchNode
from plugins.amazon.nodes.transform_nodes import FilterNode, SortNode
from plugins.amazon.nodes.sink_nodes import (
    MarketAnalysisNode,
    OpportunityAnalysisNode,
    CompetitionAnalysisNode,
    SalesAnalysisNode,
    ReviewAnalysisNode,
    MarketScoreNode,
    ChartOutputNode,
    ReportOutputNode,
    JSONOutputNode,
)


def register():
    """Register all Amazon plugin nodes with the gateway."""
    register_nodes("amazon", [
        # Data fetching (graph entry points)
        KeywordSearchNode(),
        CategorySearchNode(),
        # Data transformation
        FilterNode(),
        SortNode(),
        # Analysis
        MarketAnalysisNode(),
        OpportunityAnalysisNode(),
        CompetitionAnalysisNode(),
        SalesAnalysisNode(),
        ReviewAnalysisNode(),
        # Multi-input aggregation
        MarketScoreNode(),
        # Output
        ChartOutputNode(),
        ReportOutputNode(),
        JSONOutputNode(),
    ])
