"""Amazon Plugin — Filtering/Sorting Nodes (ProductCollection → ProductCollection)"""

from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.amazon.repository.product_repository import ProductCollection as ProductData
from plugins.amazon.artifact_types import ProductCollection, FilteredProductCollection


class FilterNode(Node):
    """Filter product collection by multiple conditions (AND semantics)."""

    name = "filter"
    plugin = "amazon"
    description = "Filter products by price, review count, rating, and category — all conditions are ANDed"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Product collection to filter",
        ),
    }

    output_spec = OutputSpec(
        key="filtered_products",
        artifact_type=FilteredProductCollection,
        description="Filtered product collection",
    )

    parameter_specs = {
        "price_gte": ParameterSpec("price_gte", float, required=False,
                                   description="Minimum price"),
        "price_lte": ParameterSpec("price_lte", float, required=False,
                                   description="Maximum price"),
        "review_lt": ParameterSpec("review_lt", int, required=False,
                                   description="Review count less than"),
        "review_gte": ParameterSpec("review_gte", int, required=False,
                                    description="Review count greater or equal"),
        "rating_gte": ParameterSpec("rating_gte", float, required=False,
                                    description="Minimum rating"),
        "category": ParameterSpec("category", str, required=False,
                                  description="Category name filter"),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data

        if "price_gte" in params:
            products = products.filter_price_gte(float(params["price_gte"]))
        if "price_lte" in params:
            products = products.filter_price_lte(float(params["price_lte"]))
        if "review_lt" in params:
            products = products.filter_review_lt(int(params["review_lt"]))
        if "review_gte" in params:
            products = products.filter_review_gte(int(params["review_gte"]))
        if "rating_gte" in params:
            products = products.filter_review_rating_gte(float(params["rating_gte"]))
        if "category" in params:
            products = products.filter_category(params["category"])

        return Artifact(
            key=self.output_spec.key,
            type=FilteredProductCollection,
            data=products,
            produced_by=self.name,
            metadata={"count": len(products)},
        )


class SortNode(Node):
    """Sort product collection by a specified field."""

    name = "sort"
    plugin = "amazon"
    description = "Sort products by price, review count, or monthly sales"

    input_specs = {
        "products": InputSpec(
            name="products",
            artifact_type=ProductCollection,
            required=True,
            description="Product collection to sort",
        ),
    }

    output_spec = OutputSpec(
        key="sorted_products",
        artifact_type=ProductCollection,
        description="Sorted product collection",
    )

    parameter_specs = {
        "by": ParameterSpec("by", str, required=True,
                            description="Sort field: price, review, sales"),
        "order": ParameterSpec("order", str, required=False, default="desc",
                               description="Sort order: asc or desc"),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        products: ProductData = inputs["products"].data
        sort_by = params.get("by", "sales")
        order = params.get("order", "desc")

        if sort_by == "price":
            products = products.sort_by_price_desc()
            if order == "asc":
                products = ProductData(list(reversed(products.products)))
        elif sort_by == "review":
            products = products.sort_by_review_asc()
            if order == "desc":
                products = ProductData(list(reversed(products.products)))
        elif sort_by == "sales":
            products = products.sort_by_sales_desc()
            if order == "asc":
                products = ProductData(list(reversed(products.products)))

        return Artifact(
            key=self.output_spec.key,
            type=ProductCollection,
            data=products,
            produced_by=self.name,
            metadata={"count": len(products), "sort_by": sort_by, "order": order},
        )
