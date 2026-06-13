"""Amazon DB Plugin — Filtering/Sorting Nodes (ProductCollection → ProductCollection)"""

from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.amazon_db.repository.product_repository import ProductCollection as ProductData
from plugins.amazon_db.artifact_types import ProductCollection, FilteredProductCollection


class FilterNode(Node):
    """Filter product collection by multiple conditions (AND semantics).

    Supports filtering by price, reviews, rating, margin, FBA fee, sales amount,
    category, category rank, and launch days.
    """

    name = "filter"
    plugin = "amazon_db"
    description = (
        "Filter products by price, review count, rating, margin, FBA fee, "
        "sales amount, category, category rank, and launch days — all conditions are ANDed"
    )

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
        # Price
        "price_gte": ParameterSpec("price_gte", float, required=False,
                                   description="Minimum price"),
        "price_lte": ParameterSpec("price_lte", float, required=False,
                                   description="Maximum price"),
        # Reviews
        "review_lt": ParameterSpec("review_lt", int, required=False,
                                   description="Review count less than"),
        "review_gte": ParameterSpec("review_gte", int, required=False,
                                    description="Review count greater or equal"),
        # Rating
        "rating_gte": ParameterSpec("rating_gte", float, required=False,
                                    description="Minimum rating (0-5)"),
        # Category
        "category": ParameterSpec("category", str, required=False,
                                  description="Exact parent_category name"),
        "parent_category": ParameterSpec("parent_category", str, required=False,
                                         description="Exact parent_category name"),
        "sub_category": ParameterSpec("sub_category", str, required=False,
                                      description="Exact sub_category name"),
        # Margin
        "margin_gte": ParameterSpec("margin_gte", float, required=False,
                                    description="Minimum gross margin (e.g. 0.3 = 30%)"),
        "margin_lte": ParameterSpec("margin_lte", float, required=False,
                                    description="Maximum gross margin"),
        # FBA fee
        "fba_fee_lte": ParameterSpec("fba_fee_lte", float, required=False,
                                     description="Maximum FBA fee"),
        "fba_fee_gte": ParameterSpec("fba_fee_gte", float, required=False,
                                     description="Minimum FBA fee"),
        # Sales amount
        "sales_amount_gte": ParameterSpec("sales_amount_gte", float, required=False,
                                          description="Minimum total sales amount (revenue)"),
        # Launch days
        "launch_days_lte": ParameterSpec("launch_days_lte", int, required=False,
                                         description="Maximum days since launch"),
        "launch_days_gte": ParameterSpec("launch_days_gte", int, required=False,
                                         description="Minimum days since launch"),
        # Category rank
        "parent_category_rank_lte": ParameterSpec("parent_category_rank_lte", int, required=False,
                                                  description="Maximum parent category rank (lower = better)"),
        "sub_category_rank_lte": ParameterSpec("sub_category_rank_lte", int, required=False,
                                               description="Maximum sub category rank (lower = better)"),
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
        if "parent_category" in params:
            products = products.filter_parent_category(params["parent_category"])
        if "sub_category" in params:
            products = products.filter_sub_category(params["sub_category"])
        if "margin_gte" in params:
            products = products.filter_margin_gte(float(params["margin_gte"]))
        if "margin_lte" in params:
            products = products.filter_margin_lte(float(params["margin_lte"]))
        if "fba_fee_lte" in params:
            products = products.filter_fba_fee_lte(float(params["fba_fee_lte"]))
        if "fba_fee_gte" in params:
            products = products.filter_fba_fee_gte(float(params["fba_fee_gte"]))
        if "sales_amount_gte" in params:
            products = products.filter_sales_amount_gte(float(params["sales_amount_gte"]))
        if "launch_days_lte" in params:
            products = products.filter_launch_days_lte(int(params["launch_days_lte"]))
        if "launch_days_gte" in params:
            products = products.filter_launch_days_gte(int(params["launch_days_gte"]))
        if "parent_category_rank_lte" in params:
            products = products.filter_parent_category_rank_lte(int(params["parent_category_rank_lte"]))
        if "sub_category_rank_lte" in params:
            products = products.filter_sub_category_rank_lte(int(params["sub_category_rank_lte"]))

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
    plugin = "amazon_db"
    description = "Sort products by price, review count, monthly sales, sales amount, margin, FBA fee, launch days, or category rank"

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
                            description="Sort field: price, review, sales, sales_amount, margin, fba_fee, launch_days, parent_category_rank"),
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
        elif sort_by == "sales_amount":
            products = products.sort_by_sales_amount_desc()
            if order == "asc":
                products = ProductData(list(reversed(products.products)))
        elif sort_by == "margin":
            products = products.sort_by_margin_desc()
            if order == "asc":
                products = ProductData(list(reversed(products.products)))
        elif sort_by == "fba_fee":
            products = products.sort_by_fba_fee_asc()
            if order == "desc":
                products = ProductData(list(reversed(products.products)))
        elif sort_by == "launch_days":
            products = products.sort_by_launch_days_asc()
            if order == "desc":
                products = ProductData(list(reversed(products.products)))
        elif sort_by == "parent_category_rank":
            products = products.sort_by_parent_category_rank_asc()
            if order == "desc":
                products = ProductData(list(reversed(products.products)))

        return Artifact(
            key=self.output_spec.key,
            type=ProductCollection,
            data=products,
            produced_by=self.name,
            metadata={"count": len(products), "sort_by": sort_by, "order": order},
        )
