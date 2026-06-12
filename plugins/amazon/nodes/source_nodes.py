"""Amazon Plugin - Source Nodes"""

from core.node import Node, NodeType
from core.execution_context import ExecutionContext
from plugins.amazon.repository.product_repository import ProductRepository


class KeywordSearchNode(Node):
    """Search products by keyword with fuzzy matching"""

    name = "search_by_keyword"
    description = "Search products by keyword, supports fuzzy matching on title and keyword fields"
    node_type = NodeType.SOURCE
    parameters = {
        "keyword": {"type": "string", "required": True, "description": "Search keyword"},
        "limit": {"type": "integer", "required": False, "default": 100, "description": "Max results"},
    }
    output_schema = {"type": "ProductCollection"}

    def __init__(self):
        self._repository = ProductRepository()

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        keyword = context.current_params.get("keyword", "")
        limit_str = context.current_params.get("limit", "100")
        limit = int(limit_str) if limit_str else 100

        products = self._repository.search_by_keyword(keyword)
        if limit > 0:
            products = products.limit(limit)

        context.metadata["rows_processed"] = len(products)
        context.metadata["keyword"] = keyword
        context.data = products
        return context


class CategorySearchNode(Node):
    """Search products by category"""

    name = "search_by_category"
    description = "Search products by category"
    node_type = NodeType.SOURCE
    parameters = {
        "category": {"type": "string", "required": True, "description": "Product category"},
    }
    output_schema = {"type": "ProductCollection"}

    def __init__(self):
        self._repository = ProductRepository()

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        category = context.current_params.get("category", "")
        products = self._repository.search_by_category(category)

        context.metadata["rows_processed"] = len(products)
        context.metadata["category"] = category
        context.data = products
        return context
