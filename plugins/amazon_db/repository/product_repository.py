"""Amazon DB plugin — data access layer

Defines the Product data model, ProductCollection (immutable, chainable container),
and ProductRepository backed by the real SQLite database.

See plugins/amazon_db/services/market_service.py for the Service layer that
consumes ProductCollection.
"""

from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import func

from .db import get_session
from .models import Product as ProductOrm, ProductKeyword as ProductKeywordOrm


def _coalesce(value, default):
    """Return value if not None, else default."""
    return default if value is None else value


@dataclass
class Product:
    """Product data model — mirrors the real database columns."""
    asin: str
    title: str
    price: float
    review_count: int
    rating: float
    monthly_sales: int
    sales_amount: float
    fba_fee: float
    gross_margin: float
    parent_category: str
    parent_category_rank: int
    sub_category: str
    sub_category_rank: int
    launch_date: str | None = None
    launch_days: int = 0
    keyword: str = ""
    url: str = ""
    image_path: str = ""

    @classmethod
    def from_orm(cls, row: ProductOrm, keyword: str = "") -> "Product":
        """Build a Product from a SQLAlchemy ORM row."""
        return cls(
            asin=row.asin,
            title=row.title or "",
            price=float(_coalesce(row.price, 0.0)),
            review_count=row.review_count or 0,
            rating=float(_coalesce(row.rating, 0.0)),
            monthly_sales=row.monthly_sales or 0,
            sales_amount=float(_coalesce(row.sales_amount, 0.0)),
            fba_fee=float(_coalesce(row.fba_fee, 0.0)),
            gross_margin=float(_coalesce(row.gross_margin, 0.0)),
            parent_category=row.parent_category or "",
            parent_category_rank=row.parent_category_rank or 0,
            sub_category=row.sub_category or "",
            sub_category_rank=row.sub_category_rank or 0,
            launch_date=row.launch_date.isoformat() if row.launch_date else None,
            launch_days=row.launch_days or 0,
            keyword=keyword,
            url=row.url or "",
            image_path=row.image_path or "",
        )


class ProductCollection:
    """Immutable in-memory product container with chainable filter/sort/aggregate methods.

    Each filter/sort returns a NEW ProductCollection — the original is never mutated.
    This matches the mock plugin's pattern — each filter/sort returns a new instance.
    """

    def __init__(self, products: list[Product] | None = None):
        self._products: list[Product] = products or []

    def __len__(self) -> int:
        return len(self._products)

    def __iter__(self):
        return iter(self._products)

    @property
    def products(self) -> list[Product]:
        return self._products

    # ---- price filters ----

    def filter_price_gte(self, min_price: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.price >= min_price])

    def filter_price_lte(self, max_price: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.price <= max_price])

    # ---- review filters ----

    def filter_review_lt(self, max_review: int) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.review_count < max_review])

    def filter_review_gte(self, min_review: int) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.review_count >= min_review])

    def filter_review_rating_gte(self, min_rating: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.rating >= min_rating])

    # ---- category filters ----

    def filter_category(self, category: str) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.parent_category == category])

    def filter_parent_category(self, category: str) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.parent_category == category])

    def filter_sub_category(self, category: str) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.sub_category == category])

    # ---- margin / profit filters ----

    def filter_margin_gte(self, min_margin: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.gross_margin >= min_margin])

    def filter_margin_lte(self, max_margin: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.gross_margin <= max_margin])

    # ---- FBA fee filters ----

    def filter_fba_fee_gte(self, min_fee: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.fba_fee >= min_fee])

    def filter_fba_fee_lte(self, max_fee: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.fba_fee <= max_fee])

    # ---- sales amount filters ----

    def filter_sales_amount_gte(self, min_amount: float) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.sales_amount >= min_amount])

    # ---- launch date filters ----

    def filter_launch_days_lte(self, max_days: int) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.launch_days <= max_days])

    def filter_launch_days_gte(self, min_days: int) -> "ProductCollection":
        return ProductCollection([p for p in self._products if p.launch_days >= min_days])

    # ---- category rank filters ----

    def filter_parent_category_rank_lte(self, max_rank: int) -> "ProductCollection":
        return ProductCollection([p for p in self._products if 0 < p.parent_category_rank <= max_rank])

    def filter_sub_category_rank_lte(self, max_rank: int) -> "ProductCollection":
        return ProductCollection([p for p in self._products if 0 < p.sub_category_rank <= max_rank])

    # ---- sort methods ----

    def sort_by_price_desc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.price, reverse=True))

    def sort_by_review_asc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.review_count))

    def sort_by_sales_desc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.monthly_sales, reverse=True))

    def sort_by_sales_amount_desc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.sales_amount, reverse=True))

    def sort_by_margin_desc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.gross_margin, reverse=True))

    def sort_by_fba_fee_asc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.fba_fee))

    def sort_by_launch_days_asc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.launch_days))

    def sort_by_parent_category_rank_asc(self) -> "ProductCollection":
        return ProductCollection(sorted(self._products, key=lambda p: p.parent_category_rank if p.parent_category_rank > 0 else 999999))

    def limit(self, n: int) -> "ProductCollection":
        return ProductCollection(self._products[:n])

    # ---- aggregation ----

    def avg_price(self) -> float:
        if not self._products:
            return 0.0
        return round(sum(p.price for p in self._products) / len(self._products), 2)

    def avg_rating(self) -> float:
        if not self._products:
            return 0.0
        return round(sum(p.rating for p in self._products) / len(self._products), 2)

    def avg_margin(self) -> float:
        if not self._products:
            return 0.0
        return round(sum(p.gross_margin for p in self._products) / len(self._products), 4)

    def avg_fba_fee(self) -> float:
        if not self._products:
            return 0.0
        return round(sum(p.fba_fee for p in self._products) / len(self._products), 2)

    def total_sales(self) -> int:
        return sum(p.monthly_sales for p in self._products)

    def total_sales_amount(self) -> float:
        return round(sum(p.sales_amount for p in self._products), 2)

    def price_range(self) -> tuple[float, float]:
        if not self._products:
            return (0.0, 0.0)
        prices = [p.price for p in self._products]
        return (min(prices), max(prices))

    def margin_range(self) -> tuple[float, float]:
        if not self._products:
            return (0.0, 0.0)
        margins = [p.gross_margin for p in self._products]
        return (min(margins), max(margins))

    def fba_fee_range(self) -> tuple[float, float]:
        if not self._products:
            return (0.0, 0.0)
        fees = [p.fba_fee for p in self._products]
        return (min(fees), max(fees))

    def category_breakdown(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in self._products:
            cat = p.parent_category or "(unknown)"
            counts[cat] = counts.get(cat, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def sub_category_breakdown(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in self._products:
            cat = p.sub_category or "(unknown)"
            counts[cat] = counts.get(cat, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def to_summary(self) -> dict:
        """Return a summary dict (counts / averages only, no raw product data)."""
        return {
            "count": len(self._products),
            "avg_price": self.avg_price(),
            "avg_rating": self.avg_rating(),
            "avg_margin": self.avg_margin(),
            "avg_fba_fee": self.avg_fba_fee(),
            "total_monthly_sales": self.total_sales(),
            "total_sales_amount": self.total_sales_amount(),
            "price_range": self.price_range(),
            "margin_range": self.margin_range(),
            "fba_fee_range": self.fba_fee_range(),
        }


# ================================================================
# Repository — SQL-backed data access
# ================================================================

class ProductRepository:
    """Data access backed by the real SQLite database.

    Each query method opens a fresh SQLAlchemy session, executes the query,
    materialises results into plain Product dataclass instances, and closes
    the session.

    Usage inside a Node's execute()::

        repo = ProductRepository()
        products = repo.search_by_keyword("halloween garland")
        # products is a ProductCollection — fully detached from the DB
    """

    def search_by_keyword(self, keyword: str) -> ProductCollection:
        """Search products by keyword via JOIN with product_keyword table.

        Matches against product_keyword.keyword using ILIKE (case-insensitive).
        """
        session = get_session()
        try:
            rows = (
                session.query(ProductOrm, ProductKeywordOrm.keyword)
                .join(ProductKeywordOrm, ProductOrm.asin == ProductKeywordOrm.asin)
                .filter(ProductKeywordOrm.keyword.ilike(f"%{keyword}%"))
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
                .distinct()
                .all()
            )
            results = []
            seen: set[str] = set()
            for row, kw in rows:
                if row.asin not in seen:
                    seen.add(row.asin)
                    results.append(Product.from_orm(row, keyword=kw or ""))
            return ProductCollection(results)
        finally:
            session.close()

    def search_by_category(self, category: str) -> ProductCollection:
        """Search products by parent_category or sub_category (ILIKE match)."""
        session = get_session()
        try:
            rows = (
                session.query(ProductOrm)
                .filter(
                    (ProductOrm.parent_category.ilike(f"%{category}%"))
                    | (ProductOrm.sub_category.ilike(f"%{category}%"))
                )
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
                .all()
            )
            return ProductCollection([Product.from_orm(r) for r in rows])
        finally:
            session.close()

    def search_by_parent_category(self, category: str) -> ProductCollection:
        """Exact match on parent_category."""
        session = get_session()
        try:
            rows = (
                session.query(ProductOrm)
                .filter(ProductOrm.parent_category == category)
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
                .all()
            )
            return ProductCollection([Product.from_orm(r) for r in rows])
        finally:
            session.close()

    def lookup_by_asin(self, asin: str) -> ProductCollection:
        """Exact ASIN lookup (returns 0 or 1 product)."""
        session = get_session()
        try:
            rows = (
                session.query(ProductOrm)
                .filter(ProductOrm.asin == asin)
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
                .all()
            )
            # Also fetch the first associated keyword for context
            if rows:
                kw_row = (
                    session.query(ProductKeywordOrm)
                    .filter(ProductKeywordOrm.asin == asin)
                    .first()
                )
                kw = kw_row.keyword if kw_row else ""
                return ProductCollection([Product.from_orm(rows[0], keyword=kw)])
            return ProductCollection([])
        finally:
            session.close()

    def get_all(self) -> ProductCollection:
        """Return all non-deleted products. Use with caution — 18K rows."""
        session = get_session()
        try:
            rows = (
                session.query(ProductOrm)
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
                .all()
            )
            return ProductCollection([Product.from_orm(r) for r in rows])
        finally:
            session.close()


# ================================================================
# KeywordRepository — Keyword-level SQL GROUP BY aggregation
# ================================================================

class KeywordRepository:
    """SQL-backed keyword-level aggregation queries.

    Each method performs JOIN + GROUP BY keyword and returns list[dict]
    with both basic aggregates and raw value lists for Python-level
    statistical computation (median, quartiles, Gini coefficient, etc.).

    Each method opens a fresh session and closes it before returning.
    """

    # ------------------------------------------------------------------
    # 1. Market size stats — GROUP BY keyword
    # ------------------------------------------------------------------

    def aggregate_market_stats(
        self,
        keyword_filter: str | None = None,
    ) -> list[dict]:
        """Per-keyword market size metrics: product count, total/avg reviews,
        and raw review values for median / Top3 computation."""
        session = get_session()
        try:
            # Build base subquery: keyword → asin + review_count
            base_q = (
                session.query(
                    ProductKeywordOrm.keyword,
                    ProductOrm.asin,
                    ProductOrm.review_count,
                )
                .join(ProductOrm, ProductOrm.asin == ProductKeywordOrm.asin)
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
            )
            if keyword_filter:
                base_q = base_q.filter(
                    ProductKeywordOrm.keyword.ilike(f"%{keyword_filter}%")
                )
            base_q = base_q.distinct()
            rows = base_q.all()

            # Group by keyword in Python (small cardinality — 98 keywords)
            from collections import defaultdict
            kw_data: dict[str, dict] = defaultdict(
                lambda: {"product_count": 0, "total_reviews": 0, "review_values": []}
            )
            seen: dict[str, set] = defaultdict(set)
            for keyword, asin, review_count in rows:
                if asin in seen[keyword]:
                    continue
                seen[keyword].add(asin)
                rv = review_count or 0
                kw_data[keyword]["product_count"] += 1
                kw_data[keyword]["total_reviews"] += rv
                kw_data[keyword]["review_values"].append(rv)

            result = []
            for kw, data in kw_data.items():
                result.append({
                    "keyword": kw,
                    "product_count": data["product_count"],
                    "total_reviews": data["total_reviews"],
                    "avg_reviews": (
                        round(data["total_reviews"] / data["product_count"], 2)
                        if data["product_count"] > 0 else 0.0
                    ),
                    "review_values": sorted(data["review_values"]),
                })
            return result
        finally:
            session.close()

    # ------------------------------------------------------------------
    # 2. Competition stats — GROUP BY keyword
    # ------------------------------------------------------------------

    def aggregate_competition_stats(
        self,
        keyword_filter: str | None = None,
    ) -> list[dict]:
        """Per-keyword competition metrics: product count, review values,
        launch_date values for computing Gini, CV, and new-product ratio."""
        session = get_session()
        try:
            base_q = (
                session.query(
                    ProductKeywordOrm.keyword,
                    ProductOrm.asin,
                    ProductOrm.review_count,
                    ProductOrm.launch_date,
                )
                .join(ProductOrm, ProductOrm.asin == ProductKeywordOrm.asin)
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
            )
            if keyword_filter:
                base_q = base_q.filter(
                    ProductKeywordOrm.keyword.ilike(f"%{keyword_filter}%")
                )
            base_q = base_q.distinct()
            rows = base_q.all()

            from collections import defaultdict
            kw_data: dict[str, dict] = defaultdict(
                lambda: {
                    "product_count": 0,
                    "total_reviews": 0,
                    "review_values": [],
                    "launch_dates": [],
                }
            )
            seen: dict[str, set] = defaultdict(set)
            for keyword, asin, review_count, launch_date in rows:
                if asin in seen[keyword]:
                    continue
                seen[keyword].add(asin)
                rv = review_count or 0
                kw_data[keyword]["product_count"] += 1
                kw_data[keyword]["total_reviews"] += rv
                kw_data[keyword]["review_values"].append(rv)
                if launch_date is not None:
                    kw_data[keyword]["launch_dates"].append(launch_date)

            result = []
            for kw, data in kw_data.items():
                result.append({
                    "keyword": kw,
                    "product_count": data["product_count"],
                    "avg_reviews": (
                        round(data["total_reviews"] / data["product_count"], 2)
                        if data["product_count"] > 0 else 0.0
                    ),
                    "review_values": sorted(data["review_values"]),
                    "launch_dates": data["launch_dates"],
                })
            return result
        finally:
            session.close()

    # ------------------------------------------------------------------
    # 3. Margin stats — GROUP BY keyword
    # ------------------------------------------------------------------

    def aggregate_margin_stats(
        self,
        keyword_filter: str | None = None,
    ) -> list[dict]:
        """Per-keyword margin statistics: count, avg, min, max, and raw
        margin values for median / quartile computation."""
        session = get_session()
        try:
            base_q = (
                session.query(
                    ProductKeywordOrm.keyword,
                    ProductOrm.asin,
                    ProductOrm.gross_margin,
                )
                .join(ProductOrm, ProductOrm.asin == ProductKeywordOrm.asin)
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
                .filter(ProductOrm.gross_margin.isnot(None))
            )
            if keyword_filter:
                base_q = base_q.filter(
                    ProductKeywordOrm.keyword.ilike(f"%{keyword_filter}%")
                )
            base_q = base_q.distinct()
            rows = base_q.all()

            from collections import defaultdict
            kw_data: dict[str, dict] = defaultdict(
                lambda: {"product_count": 0, "margin_values": []}
            )
            seen: dict[str, set] = defaultdict(set)
            for keyword, asin, margin in rows:
                if asin in seen[keyword]:
                    continue
                seen[keyword].add(asin)
                kw_data[keyword]["product_count"] += 1
                kw_data[keyword]["margin_values"].append(float(margin) if margin else 0.0)

            result = []
            for kw, data in kw_data.items():
                margins = data["margin_values"]
                result.append({
                    "keyword": kw,
                    "product_count": data["product_count"],
                    "avg_margin": round(sum(margins) / len(margins), 4) if margins else 0.0,
                    "min_margin": round(min(margins), 4) if margins else 0.0,
                    "max_margin": round(max(margins), 4) if margins else 0.0,
                    "margin_values": sorted(margins),
                })
            return result
        finally:
            session.close()

    # ------------------------------------------------------------------
    # 4. Launch trend — GROUP BY keyword + launch year
    # ------------------------------------------------------------------

    def aggregate_launch_trend(
        self,
        keyword_filter: str | None = None,
    ) -> list[dict]:
        """Per-keyword + per-year launch statistics: product count,
        avg reviews by launch year."""
        session = get_session()
        try:
            base_q = (
                session.query(
                    ProductKeywordOrm.keyword,
                    ProductOrm.asin,
                    ProductOrm.launch_date,
                    ProductOrm.review_count,
                )
                .join(ProductOrm, ProductOrm.asin == ProductKeywordOrm.asin)
                .filter(ProductOrm.is_deleted == False)  # noqa: E712
                .filter(ProductOrm.launch_date.isnot(None))
            )
            if keyword_filter:
                base_q = base_q.filter(
                    ProductKeywordOrm.keyword.ilike(f"%{keyword_filter}%")
                )
            base_q = base_q.distinct()
            rows = base_q.all()

            from collections import defaultdict
            kw_year: dict[str, dict[int, dict]] = defaultdict(
                lambda: defaultdict(lambda: {"count": 0, "total_reviews": 0})
            )
            kw_total: dict[str, int] = defaultdict(int)
            seen: dict[str, set] = defaultdict(set)

            for keyword, asin, launch_date, review_count in rows:
                if asin in seen[keyword]:
                    continue
                seen[keyword].add(asin)
                year = launch_date.year
                kw_year[keyword][year]["count"] += 1
                kw_year[keyword][year]["total_reviews"] += review_count or 0
                kw_total[keyword] += 1

            result = []
            for kw, year_data in kw_year.items():
                entry: dict = {"keyword": kw, "total_products": kw_total[kw]}
                for yr in range(2020, 2027):
                    d = year_data.get(yr, {"count": 0, "total_reviews": 0})
                    entry[f"products_{yr}"] = d["count"]
                    entry[f"avg_reviews_{yr}"] = (
                        round(d["total_reviews"] / d["count"], 1)
                        if d["count"] > 0 else 0
                    )
                result.append(entry)
            return result
        finally:
            session.close()
