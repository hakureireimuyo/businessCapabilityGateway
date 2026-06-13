"""Amazon Plugin — Data-fetching Nodes (no inputs, produce ProductCollection)"""

from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.amazon.repository.product_repository import ProductRepository
from plugins.amazon.artifact_types import ProductCollection


class KeywordSearchNode(Node):
    """Search products by keyword with fuzzy matching."""

    name = "keyword_search"
    plugin = "amazon"
    description = "Search products by keyword, supports fuzzy matching on title and keyword fields"

    input_specs = {}  # No inputs — this is a graph entry point

    output_spec = OutputSpec(
        key="products",
        artifact_type=ProductCollection,
        description="Matching products",
    )

    parameter_specs = {
        "keyword": ParameterSpec("keyword", str, required=True,
                                 description="Search keyword"),
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
    """Search products by category."""

    name = "category_search"
    plugin = "amazon"
    description = "Search products by category"

    input_specs = {}

    output_spec = OutputSpec(
        key="products",
        artifact_type=ProductCollection,
        description="Products in category",
    )

    parameter_specs = {
        "category": ParameterSpec("category", str, required=True,
                                  description="Product category"),
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
        products = self._repository.search_by_category(category)

        return Artifact(
            key=self.output_spec.key,
            type=ProductCollection,
            data=products,
            produced_by=self.name,
            metadata={"count": len(products), "category": category},
        )
