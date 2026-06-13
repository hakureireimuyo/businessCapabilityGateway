"""Amazon DB Plugin — Analysis & Output Nodes

These nodes consume ProductCollection data and produce final structured results.
They follow: unpack Artifact → call Service → pack result into Artifact.

All analysis nodes return aggregated summaries (high-dimension semantics),
never raw per-item or per-keyword lists. See the boundary principle in
docs/节点协议与规范.md.

For the Service layer, see plugins/amazon_db/services/market_service.py.
"""

import json
from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, ArtifactType, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.amazon_db.repository.product_repository import ProductCollection as ProductData
from plugins.amazon_db.services.market_service import MarketService
from plugins.amazon_db.artifact_types import (
    ProductCollection,
    MarketAnalysis,
    CompetitionAnalysis,
    SalesMetrics,
    ReviewMetrics,
    MarketSignal,
    ChartData,
    JSONData,
    OpportunitySummary,
    ScoringSummary,
    DiagnosisSummary,
    KeywordMarketSummary,
    KeywordCompetitionSummary,
    KeywordMarginSummary,
    KeywordTrendSummary,
)


# ================================================================
# Product-level Analysis Nodes (aggregated output)
# ================================================================

class MarketAnalysisNode(Node):
    """Analyze market: size, avg price, competition score, margin stats."""

    name = "market_analysis"
    plugin = "amazon_db"
    description = "Analyze market: size, avg price, avg margin, competition score (0-100), sales distribution"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze",
        ),
    }

    output_spec = OutputSpec(
        key="market_analysis",
        artifact_type=MarketAnalysis,
        description="Market analysis result",
    )

    parameter_specs = {}

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        result = MarketService.analyze_market(products)

        return Artifact(
            key=self.output_spec.key,
            type=MarketAnalysis,
            data=result,
            produced_by=self.name,
        )


class OpportunityAnalysisNode(Node):
    """Find low-competition high-opportunity products.

    Returns aggregated summary: total scanned, opportunity count,
    avg score/price/margin, and top N opportunities.
    """

    name = "opportunity_analysis"
    plugin = "amazon_db"
    description = "Identify market opportunities: low-review high-rating products. Returns summary + top opportunities"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to scan for opportunities",
        ),
    }

    output_spec = OutputSpec(
        key="opportunity_summary",
        artifact_type=OpportunitySummary,
        description="Opportunity analysis: aggregated summary + top opportunities",
    )

    parameter_specs = {
        "max_review": ParameterSpec("max_review", int, required=False, default=100,
                                    description="Max review count threshold for opportunity"),
        "top_n": ParameterSpec("top_n", int, required=False, default=10,
                               description="Number of top opportunities to return"),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        max_review = params.get("max_review", 100)
        top_n = params.get("top_n", 10)
        result = MarketService.find_opportunities(products, max_review, top_n=top_n)

        return Artifact(
            key=self.output_spec.key,
            type=OpportunitySummary,
            data=result,
            produced_by=self.name,
        )


class CompetitionAnalysisNode(Node):
    """Assess market competition landscape."""

    name = "competition_analysis"
    plugin = "amazon_db"
    description = "Assess market competition: high/low-end distribution, dominant players, entry barrier score"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze",
        ),
    }

    output_spec = OutputSpec(
        key="competition_analysis",
        artifact_type=CompetitionAnalysis,
        description="Competition analysis result",
    )

    parameter_specs = {}

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        result = MarketService.competition_analysis(products)

        return Artifact(
            key=self.output_spec.key,
            type=CompetitionAnalysis,
            data=result,
            produced_by=self.name,
        )


class SalesAnalysisNode(Node):
    """Statistical analysis of sales data."""

    name = "sales_analysis"
    plugin = "amazon_db"
    description = "Analyze sales distribution: total sales, avg sales, total revenue, top sellers"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze sales for",
        ),
    }

    output_spec = OutputSpec(
        key="sales_metrics",
        artifact_type=SalesMetrics,
        description="Sales analysis metrics",
    )

    parameter_specs = {}

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        result = MarketService.analyze_sales(products)

        return Artifact(
            key=self.output_spec.key,
            type=SalesMetrics,
            data=result,
            produced_by=self.name,
        )


class ReviewAnalysisNode(Node):
    """Statistical analysis of review data."""

    name = "review_analysis"
    plugin = "amazon_db"
    description = "Analyze review distribution: avg rating, total reviews, avg reviews per product"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze reviews for",
        ),
    }

    output_spec = OutputSpec(
        key="review_metrics",
        artifact_type=ReviewMetrics,
        description="Review analysis metrics",
    )

    parameter_specs = {}

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        result = MarketService.analyze_reviews(products)

        return Artifact(
            key=self.output_spec.key,
            type=ReviewMetrics,
            data=result,
            produced_by=self.name,
        )


class MarketScoreNode(Node):
    """Aggregate multiple metrics into a market signal.

    This demonstrates a multi-input node: it consumes two distinct
    metric types and produces an aggregated result.
    """

    name = "market_score"
    plugin = "amazon_db"
    description = "Compute aggregate market score from sales and review metrics"

    input_specs = {
        "sales": InputSpec(
            name="sales",
            artifact_type=SalesMetrics,
            required=True,
            description="Sales metrics input",
        ),
        "reviews": InputSpec(
            name="reviews",
            artifact_type=ReviewMetrics,
            required=True,
            description="Review metrics input",
        ),
    }

    output_spec = OutputSpec(
        key="market_signal",
        artifact_type=MarketSignal,
        description="Aggregated market signal",
    )

    parameter_specs = {
        "method": ParameterSpec("method", str, required=False, default="weighted",
                                description="Scoring method: weighted | simple"),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        sales_data = inputs["sales"].data
        review_data = inputs["reviews"].data
        method = params.get("method", "weighted")
        result = MarketService.compute_market_score(sales_data, review_data, method)

        return Artifact(
            key=self.output_spec.key,
            type=MarketSignal,
            data=result,
            produced_by=self.name,
        )


# ================================================================
# Product Scoring & Diagnosis Nodes (aggregated output)
# ================================================================

class ProductScoringNode(Node):
    """Multi-dimension weighted product scoring with aggregated summary.

    Returns score distribution + top N products, never raw per-item lists.
    """

    name = "product_scoring"
    plugin = "amazon_db"
    description = (
        "Score products on 4 dimensions (profit/competition/quality/freshness) "
        "using percentile ranking within keyword group. Returns score distribution "
        "summary + top N products."
    )

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to score",
        ),
    }

    output_spec = OutputSpec(
        key="scoring_summary",
        artifact_type=ScoringSummary,
        description="Product scoring: distribution summary + top products",
    )

    parameter_specs = {
        "weight_profit": ParameterSpec(
            "weight_profit", float, required=False, default=0.40,
            description="Weight for profit dimension (gross_margin percentile)",
        ),
        "weight_competition": ParameterSpec(
            "weight_competition", float, required=False, default=0.30,
            description="Weight for competition dimension (inverse review_count percentile)",
        ),
        "weight_quality": ParameterSpec(
            "weight_quality", float, required=False, default=0.20,
            description="Weight for quality dimension (rating percentile)",
        ),
        "weight_freshness": ParameterSpec(
            "weight_freshness", float, required=False, default=0.10,
            description="Weight for freshness dimension (inverse launch_days percentile)",
        ),
        "top_n": ParameterSpec(
            "top_n", int, required=False, default=10,
            description="Number of top products to return in detail",
        ),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        result = MarketService.score_products(
            products,
            weight_profit=params.get("weight_profit", 0.40),
            weight_competition=params.get("weight_competition", 0.30),
            weight_quality=params.get("weight_quality", 0.20),
            weight_freshness=params.get("weight_freshness", 0.10),
            top_n=params.get("top_n", 10),
        )
        return Artifact(
            key=self.output_spec.key,
            type=ScoringSummary,
            data=result,
            produced_by=self.name,
        )


class ProductDiagnosisNode(Node):
    """Comprehensive product diagnosis with aggregated summary.

    Returns category counts + top N per diagnosis type, never raw per-item lists.
    """

    name = "product_diagnosis"
    plugin = "amazon_db"
    description = (
        "Diagnose products: identify promising new products, declining old products, "
        "potential star performers, and reputation crisis products. "
        "Returns category summary counts + top N per category."
    )

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to diagnose",
        ),
    }

    output_spec = OutputSpec(
        key="diagnosis_summary",
        artifact_type=DiagnosisSummary,
        description="Product diagnosis: category counts + top N per category",
    )

    parameter_specs = {
        "top_n": ParameterSpec(
            "top_n", int, required=False, default=10,
            description="Number of top products to return per diagnosis category",
        ),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        top_n = params.get("top_n", 10)
        result = MarketService.diagnose_products(products, top_n=top_n)
        return Artifact(
            key=self.output_spec.key,
            type=DiagnosisSummary,
            data=result,
            produced_by=self.name,
        )


# ================================================================
# Keyword-level Analysis Nodes (aggregated output)
# ================================================================

class KeywordMarketAnalysisNode(Node):
    """Per-keyword market size analysis with aggregated summary.

    Returns market-size distribution + top N keywords, never raw per-keyword lists.
    """

    name = "keyword_market_analysis"
    plugin = "amazon_db"
    description = (
        "Analyze market size across keywords: total products/reviews, "
        "market size distribution (大型/中型/小型/小众), monopoly count, top N markets"
    )

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze by keyword",
        ),
    }

    output_spec = OutputSpec(
        key="keyword_market_summary",
        artifact_type=KeywordMarketSummary,
        description="Keyword market analysis: size distribution + top keywords",
    )

    parameter_specs = {
        "keyword_filter": ParameterSpec(
            "keyword_filter", str, required=False,
            description="Optional keyword LIKE filter to narrow aggregation scope",
        ),
        "top_n": ParameterSpec(
            "top_n", int, required=False, default=10,
            description="Number of top markets to return in detail",
        ),
    }

    def __init__(self):
        from plugins.amazon_db.repository.product_repository import KeywordRepository
        self._repo = KeywordRepository()

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        keyword_filter = params.get("keyword_filter")
        top_n = params.get("top_n", 10)
        stats = self._repo.aggregate_market_stats(keyword_filter=keyword_filter)
        from plugins.amazon_db.services.market_service import KeywordAnalysisService
        result = KeywordAnalysisService.analyze_keyword_market(stats, top_n=top_n)
        return Artifact(
            key=self.output_spec.key,
            type=KeywordMarketSummary,
            data=result,
            produced_by=self.name,
        )


class KeywordCompetitionAnalysisNode(Node):
    """Per-keyword competition intensity with aggregated summary.

    Returns competition-level distribution + top N keywords, never raw per-keyword lists.
    """

    name = "keyword_competition_analysis"
    plugin = "amazon_db"
    description = (
        "Analyze competition across keywords: competition level distribution "
        "(蓝海/中等竞争/红海), avg Gini coefficient, avg new product ratio, top N keywords"
    )

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze by keyword",
        ),
    }

    output_spec = OutputSpec(
        key="keyword_competition_summary",
        artifact_type=KeywordCompetitionSummary,
        description="Keyword competition analysis: level distribution + top keywords",
    )

    parameter_specs = {
        "keyword_filter": ParameterSpec(
            "keyword_filter", str, required=False,
            description="Optional keyword LIKE filter to narrow aggregation scope",
        ),
        "top_n": ParameterSpec(
            "top_n", int, required=False, default=10,
            description="Number of top keywords to return in detail",
        ),
    }

    def __init__(self):
        from plugins.amazon_db.repository.product_repository import KeywordRepository
        self._repo = KeywordRepository()

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        keyword_filter = params.get("keyword_filter")
        top_n = params.get("top_n", 10)
        stats = self._repo.aggregate_competition_stats(keyword_filter=keyword_filter)
        from plugins.amazon_db.services.market_service import KeywordAnalysisService
        result = KeywordAnalysisService.analyze_keyword_competition(stats, top_n=top_n)
        return Artifact(
            key=self.output_spec.key,
            type=KeywordCompetitionSummary,
            data=result,
            produced_by=self.name,
        )


class KeywordMarginAnalysisNode(Node):
    """Per-keyword margin distribution with aggregated summary.

    Returns high-margin count, overall avg/median margin + top N keywords,
    never raw per-keyword lists.
    """

    name = "keyword_margin_analysis"
    plugin = "amazon_db"
    description = (
        "Analyze gross margin across keywords: high-margin keyword count, "
        "overall avg/median margin, top N keywords by margin"
    )

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze by keyword",
        ),
    }

    output_spec = OutputSpec(
        key="keyword_margin_summary",
        artifact_type=KeywordMarginSummary,
        description="Keyword margin analysis: high-margin count + top keywords",
    )

    parameter_specs = {
        "keyword_filter": ParameterSpec(
            "keyword_filter", str, required=False,
            description="Optional keyword LIKE filter to narrow aggregation scope",
        ),
        "top_n": ParameterSpec(
            "top_n", int, required=False, default=10,
            description="Number of top margin keywords to return in detail",
        ),
    }

    def __init__(self):
        from plugins.amazon_db.repository.product_repository import KeywordRepository
        self._repo = KeywordRepository()

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        keyword_filter = params.get("keyword_filter")
        top_n = params.get("top_n", 10)
        stats = self._repo.aggregate_margin_stats(keyword_filter=keyword_filter)
        from plugins.amazon_db.services.market_service import KeywordAnalysisService
        result = KeywordAnalysisService.analyze_keyword_margin(stats, top_n=top_n)
        return Artifact(
            key=self.output_spec.key,
            type=KeywordMarginSummary,
            data=result,
            produced_by=self.name,
        )


class KeywordTrendAnalysisNode(Node):
    """Per-keyword launch trend with aggregated summary.

    Returns trend distribution + growing/declining keywords, never raw per-keyword lists.
    """

    name = "keyword_trend_analysis"
    plugin = "amazon_db"
    description = (
        "Analyze launch trend across keywords: trend distribution "
        "(增长期/稳定期/可能衰退), top growing and declining keywords"
    )

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to analyze by keyword",
        ),
    }

    output_spec = OutputSpec(
        key="keyword_trend_summary",
        artifact_type=KeywordTrendSummary,
        description="Keyword trend analysis: trend distribution + growing/declining keywords",
    )

    parameter_specs = {
        "keyword_filter": ParameterSpec(
            "keyword_filter", str, required=False,
            description="Optional keyword LIKE filter to narrow aggregation scope",
        ),
        "top_n": ParameterSpec(
            "top_n", int, required=False, default=10,
            description="Number of keywords per trend category to return in detail",
        ),
    }

    def __init__(self):
        from plugins.amazon_db.repository.product_repository import KeywordRepository
        self._repo = KeywordRepository()

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        keyword_filter = params.get("keyword_filter")
        top_n = params.get("top_n", 10)
        stats = self._repo.aggregate_launch_trend(keyword_filter=keyword_filter)
        from plugins.amazon_db.services.market_service import KeywordAnalysisService
        result = KeywordAnalysisService.analyze_keyword_trend(stats, top_n=top_n)
        return Artifact(
            key=self.output_spec.key,
            type=KeywordTrendSummary,
            data=result,
            produced_by=self.name,
        )


# ================================================================
# Output Nodes (graph endpoints) — unchanged
# ================================================================

class ChartOutputNode(Node):
    """Generate chart data from any analysis result."""

    name = "chart_output"
    plugin = "amazon_db"
    description = "Format analysis results as chart visualization data"

    input_specs = {
        "data": InputSpec(
            name="data",
            artifact_type=ArtifactType,
            required=True,
            description="Any analysis result to format as chart",
        ),
    }

    output_spec = OutputSpec(
        key="chart",
        artifact_type=ChartData,
        description="Chart-ready data",
    )

    parameter_specs = {}

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        source = inputs["data"]
        chart_data = {
            "type": "bar",
            "source": source.key,
            "source_type": source.type.__name__,
            "values": source.data,
            "metadata": source.metadata,
        }
        return Artifact(
            key=self.output_spec.key,
            type=ChartData,
            data=chart_data,
            produced_by=self.name,
        )


class JSONOutputNode(Node):
    """Raw JSON output from any artifact."""

    name = "json_output"
    plugin = "amazon_db"
    description = "Return analysis results as raw JSON"

    input_specs = {
        "data": InputSpec(
            name="data",
            artifact_type=ArtifactType,
            required=True,
            description="Any artifact to output as JSON",
        ),
    }

    output_spec = OutputSpec(
        key="json",
        artifact_type=JSONData,
        description="Raw JSON data",
    )

    parameter_specs = {}

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        source = inputs["data"]
        return Artifact(
            key=self.output_spec.key,
            type=JSONData,
            data=source.data,
            produced_by=self.name,
        )
