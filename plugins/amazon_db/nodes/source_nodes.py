"""Amazon DB Plugin — Data-fetching Nodes (no inputs, produce ProductCollection)"""

from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.amazon_db.repository.product_repository import ProductRepository
from plugins.amazon_db.artifact_types import ProductCollection


class KeywordSearchNode(Node):
    """Search products by keyword via JOIN with product_keyword table."""

    name = "keyword_search"
    plugin = "amazon_db"
    description = "Search products by keyword, matches against product_keyword table with LIKE"

    input_specs = {}

    output_spec = OutputSpec(
        key="products",
        artifact_type=ProductCollection,
        description="Matching products",
    )

    parameter_specs = {
        "keyword": ParameterSpec("keyword", str, required=True,
                                 description="Search keyword (e.g. 'halloween', 'bluetooth')"),
        "limit": ParameterSpec("limit", int, required=False, default=50,
                               description="Max results to return"),
    }

    def __init__(self):
        self._repository = ProductRepository()

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        keyword = params.get("keyword", "")
        limit = params.get("limit", 50)

        products = self._repository.search_by_keyword(keyword)
        if limit and limit > 0:
            products = products.limit(limit)

        return Artifact(
            key=self.output_spec.key,
            type=ProductCollection,
            data=products,
            produced_by=self.name,
            metadata={"count": len(products), "keyword": keyword},
        )


class CategorySearchNode(Node):
    """Search products by parent_category or sub_category (ILIKE match)."""

    name = "category_search"
    plugin = "amazon_db"
    description = "Search products by category (matches parent_category and sub_category fields)"

    input_specs = {}

    output_spec = OutputSpec(
        key="products",
        artifact_type=ProductCollection,
        description="Products in matching categories",
    )

    parameter_specs = {
        "category": ParameterSpec("category", str, required=True,
                                  description="Category name to search (e.g. 'Home & Kitchen', 'Toys')"),
        "limit": ParameterSpec("limit", int, required=False, default=50,
                               description="Max results to return"),
    }

    def __init__(self):
        self._repository = ProductRepository()

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        category = params.get("category", "")
        limit = params.get("limit", 50)

        products = self._repository.search_by_category(category)
        if limit and limit > 0:
            products = products.limit(limit)

        return Artifact(
            key=self.output_spec.key,
            type=ProductCollection,
            data=products,
            produced_by=self.name,
            metadata={"count": len(products), "category": category},
        )


class AsinLookupNode(Node):
    """Look up a single product by exact ASIN."""

    name = "asin_lookup"
    plugin = "amazon_db"
    description = "Look up a specific product by its ASIN"

    input_specs = {}

    output_spec = OutputSpec(
        key="products",
        artifact_type=ProductCollection,
        description="Product matching the ASIN (0 or 1)",
    )

    parameter_specs = {
        "asin": ParameterSpec("asin", str, required=True,
                              description="Product ASIN (e.g. 'B0DXTZL9MM')"),
    }

    def __init__(self):
        self._repository = ProductRepository()

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        asin = params.get("asin", "")
        products = self._repository.lookup_by_asin(asin)

        return Artifact(
            key=self.output_spec.key,
            type=ProductCollection,
            data=products,
            produced_by=self.name,
            metadata={"count": len(products), "asin": asin},
        )
