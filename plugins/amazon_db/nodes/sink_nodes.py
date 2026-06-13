"""Amazon DB Plugin — Analysis & Output Nodes

These nodes consume ProductCollection data and produce final structured results.
They follow: unpack Artifact → call Service → pack result into Artifact.

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
    OpportunityList,
    CompetitionAnalysis,
    SalesMetrics,
    ReviewMetrics,
    MarketSignal,
    ChartData,
    JSONData,
)


# ================================================================
# Analysis Nodes
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
    """Find low-competition high-opportunity products."""

    name = "opportunity_analysis"
    plugin = "amazon_db"
    description = "Find products with low reviews and high ratings as market opportunities"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Products to scan for opportunities",
        ),
    }

    output_spec = OutputSpec(
        key="opportunity_list",
        artifact_type=OpportunityList,
        description="Identified opportunities",
    )

    parameter_specs = {
        "max_review": ParameterSpec("max_review", int, required=False, default=100,
                                    description="Max review count threshold for opportunity"),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        max_review = params.get("max_review", 100)
        result = MarketService.find_opportunities(products, max_review)

        return Artifact(
            key=self.output_spec.key,
            type=OpportunityList,
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
# Output Nodes (graph endpoints)
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
