"""Amazon Plugin - Transform Nodes"""

from core.node import Node, NodeType
from core.execution_context import ExecutionContext
from plugins.amazon.repository.product_repository import ProductCollection


class FilterNode(Node):
    """Filter product collection by price, reviews, rating, category"""

    name = "filter"
    description = "Filter product collection by price, review count, rating, and category"
    node_type = NodeType.TRANSFORM
    parameters = {
        "price_gte": {"type": "float", "required": False, "description": "Minimum price"},
        "price_lte": {"type": "float", "required": False, "description": "Maximum price"},
        "review_lt": {"type": "integer", "required": False, "description": "Review count less than"},
        "review_gte": {"type": "integer", "required": False, "description": "Review count greater or equal"},
        "rating_gte": {"type": "float", "required": False, "description": "Minimum rating"},
        "category": {"type": "string", "required": False, "description": "Category filter"},
    }
    input_schema = {"type": "ProductCollection"}
    output_schema = {"type": "ProductCollection"}

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        products: ProductCollection = context.data
        params = context.current_params

        if "price_gte" in params:
            products = products.filter_price_gte(float(params["price_gte"]))
            context.metadata["filter_price_gte"] = float(params["price_gte"])

        if "price_lte" in params:
            products = products.filter_price_lte(float(params["price_lte"]))
            context.metadata["filter_price_lte"] = float(params["price_lte"])

        if "review_lt" in params:
            products = products.filter_review_lt(int(params["review_lt"]))
            context.metadata["filter_review_lt"] = int(params["review_lt"])

        if "review_gte" in params:
            products = products.filter_review_gte(int(params["review_gte"]))
            context.metadata["filter_review_gte"] = int(params["review_gte"])

        if "rating_gte" in params:
            products = products.filter_review_rating_gte(float(params["rating_gte"]))
            context.metadata["filter_rating_gte"] = float(params["rating_gte"])

        if "category" in params:
            products = products.filter_category(params["category"])
            context.metadata["filter_category"] = params["category"]

        context.metadata["rows_after_filter"] = len(products)
        context.data = products
        return context


class SortNode(Node):
    """Sort product collection by price, review count, or sales"""

    name = "sort"
    description = "Sort product collection by price, review count, or monthly sales"
    node_type = NodeType.TRANSFORM
    parameters = {
        "by": {"type": "string", "required": True, "description": "Sort field: price, review, sales"},
        "order": {"type": "string", "required": False, "default": "desc", "description": "Sort order: asc or desc"},
    }
    input_schema = {"type": "ProductCollection"}
    output_schema = {"type": "ProductCollection"}

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        products: ProductCollection = context.data
        params = context.current_params
        sort_by = params.get("by", "sales")
        order = params.get("order", "desc")

        if sort_by == "price":
            products = products.sort_by_price_desc()
            if order == "asc":
                products = ProductCollection(list(reversed(products.products)))
        elif sort_by == "review":
            products = products.sort_by_review_asc()
            if order == "desc":
                products = ProductCollection(list(reversed(products.products)))
        elif sort_by == "sales":
            products = products.sort_by_sales_desc()
            if order == "asc":
                products = ProductCollection(list(reversed(products.products)))

        context.data = products
        return context
