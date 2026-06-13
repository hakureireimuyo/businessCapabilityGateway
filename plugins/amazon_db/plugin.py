"""Amazon DB plugin — entry point

Real-database-backed Amazon product analysis plugin.
Provides 19 nodes across five categories:
  - Data fetching (3): keyword_search, category_search, asin_lookup
  - Data transformation (2): filter, sort
  - Analysis (6): market_analysis, opportunity_analysis, competition_analysis,
                  sales_analysis, review_analysis, market_score
  - Keyword-level analysis (4): keyword_market_analysis, keyword_competition_analysis,
                                keyword_margin_analysis, keyword_trend_analysis
  - Product scoring/diagnosis (2): product_scoring, product_diagnosis
  - Output (2): chart_output, json_output
"""

from core.registry.node_registry import register_nodes
from plugins.amazon_db.nodes.source_nodes import (
    KeywordSearchNode,
    CategorySearchNode,
    AsinLookupNode,
)
from plugins.amazon_db.nodes.transform_nodes import FilterNode, SortNode
from plugins.amazon_db.nodes.sink_nodes import (
    MarketAnalysisNode,
    OpportunityAnalysisNode,
    CompetitionAnalysisNode,
    SalesAnalysisNode,
    ReviewAnalysisNode,
    MarketScoreNode,
    ChartOutputNode,
    JSONOutputNode,
    KeywordMarketAnalysisNode,
    KeywordCompetitionAnalysisNode,
    KeywordMarginAnalysisNode,
    KeywordTrendAnalysisNode,
    ProductScoringNode,
    ProductDiagnosisNode,
)


def register():
    """Register all amazon_db plugin nodes with the gateway."""
    register_nodes("amazon_db", [
        # Data fetching (graph entry points)
        KeywordSearchNode(),
        CategorySearchNode(),
        AsinLookupNode(),
        # Data transformation
        FilterNode(),
        SortNode(),
        # Product-level analysis
        MarketAnalysisNode(),
        OpportunityAnalysisNode(),
        CompetitionAnalysisNode(),
        SalesAnalysisNode(),
        ReviewAnalysisNode(),
        # Multi-input aggregation
        MarketScoreNode(),
        # Keyword-level analysis
        KeywordMarketAnalysisNode(),
        KeywordCompetitionAnalysisNode(),
        KeywordMarginAnalysisNode(),
        KeywordTrendAnalysisNode(),
        # Product scoring & diagnosis
        ProductScoringNode(),
        ProductDiagnosisNode(),
        # Output
        ChartOutputNode(),
        JSONOutputNode(),
    ])
