"""Amazon Plugin - Sink Nodes (output final results)"""

from core.node import Node, NodeType
from core.execution_context import ExecutionContext
from plugins.amazon.repository.product_repository import ProductCollection
from plugins.amazon.services.market_service import MarketService


class MarketAnalysisNode(Node):
    """Analyze market: size, avg price, competition score, sales distribution"""

    name = "market_analysis"
    description = "Analyze market competition: size, avg price, competition score (0-100, lower = blue ocean), sales distribution"
    node_type = NodeType.SINK
    parameters = {}
    input_schema = {"type": "ProductCollection"}
    output_schema = {
        "market_size": "integer",
        "avg_price": "float",
        "avg_rating": "float",
        "competition_score": "integer (0-100, lower = less competition)",
        "total_monthly_sales": "integer",
        "price_range": "[min, max]",
    }

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        products: ProductCollection = context.data
        result = MarketService.analyze_market(products)
        context.result = result
        return context


class OpportunityAnalysisNode(Node):
    """Find low-competition high-opportunity products"""

    name = "find_opportunities"
    description = "Find products with low reviews and high ratings as market opportunities"
    node_type = NodeType.SINK
    parameters = {
        "max_review": {"type": "integer", "required": False, "default": 100, "description": "Max review count threshold"},
    }
    input_schema = {"type": "ProductCollection"}
    output_schema = {
        "opportunity_count": "integer",
        "opportunities": "list of opportunity objects with scores",
    }

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        products: ProductCollection = context.data
        max_review = int(context.current_params.get("max_review", "100"))
        result = MarketService.find_opportunities(products, max_review)
        context.result = result
        return context


class CompetitionAnalysisNode(Node):
    """Assess market competition landscape"""

    name = "competition_analysis"
    description = "Assess market competition: high/low-end distribution, dominant players, entry barrier score (0-100)"
    node_type = NodeType.SINK
    parameters = {}
    input_schema = {"type": "ProductCollection"}
    output_schema = {
        "total_competitors": "integer",
        "high_end_count": "integer",
        "low_end_count": "integer",
        "avg_price": "float",
        "dominant_players": "integer",
        "entry_barrier_score": "integer (0-100)",
    }

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        products: ProductCollection = context.data
        result = MarketService.competition_analysis(products)
        context.result = result
        return context
