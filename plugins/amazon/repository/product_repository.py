"""Amazon plugin — data access layer

Defines the Product data model, ProductCollection (immutable, chainable container),
and ProductRepository.  For the Service layer that consumes these, see
plugins/amazon/services/market_service.py.
"""

from dataclasses import dataclass, field


@dataclass
class Product:
    """Product data model."""
    asin: str
    title: str
    keyword: str
    price: float
    review_count: int
    review_rating: float
    category: str
    monthly_sales: int


class ProductCollection:
    """Immutable in-memory product container with chainable filter/sort/aggregate methods."""

    def __init__(self, products: list[Product] | None = None):
        self._products: list[Product] = products or []

    def __len__(self) -> int:
        return len(self._products)

    def __iter__(self):
        return iter(self._products)

    @property
    def products(self) -> list[Product]:
        return self._products

    def filter_price_gte(self, min_price: float) -> "ProductCollection":
        return ProductCollection([
            p for p in self._products if p.price >= min_price
        ])

    def filter_price_lte(self, max_price: float) -> "ProductCollection":
        return ProductCollection([
            p for p in self._products if p.price <= max_price
        ])

    def filter_review_lt(self, max_review: int) -> "ProductCollection":
        return ProductCollection([
            p for p in self._products if p.review_count < max_review
        ])

    def filter_review_gte(self, min_review: int) -> "ProductCollection":
        return ProductCollection([
            p for p in self._products if p.review_count >= min_review
        ])

    def filter_review_rating_gte(self, min_rating: float) -> "ProductCollection":
        return ProductCollection([
            p for p in self._products if p.review_rating >= min_rating
        ])

    def filter_category(self, category: str) -> "ProductCollection":
        return ProductCollection([
            p for p in self._products if p.category == category
        ])

    def sort_by_price_desc(self) -> "ProductCollection":
        return ProductCollection(
            sorted(self._products, key=lambda p: p.price, reverse=True)
        )

    def sort_by_review_asc(self) -> "ProductCollection":
        return ProductCollection(
            sorted(self._products, key=lambda p: p.review_count)
        )

    def sort_by_sales_desc(self) -> "ProductCollection":
        return ProductCollection(
            sorted(self._products, key=lambda p: p.monthly_sales, reverse=True)
        )

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
        return round(sum(p.review_rating for p in self._products) / len(self._products), 2)

    def total_sales(self) -> int:
        return sum(p.monthly_sales for p in self._products)

    def price_range(self) -> tuple[float, float]:
        if not self._products:
            return (0.0, 0.0)
        prices = [p.price for p in self._products]
        return (min(prices), max(prices))

    def to_summary(self) -> dict:
        """Return a summary dict (counts / averages only, no raw product data)."""
        return {
            "count": len(self._products),
            "avg_price": self.avg_price(),
            "avg_rating": self.avg_rating(),
            "total_monthly_sales": self.total_sales(),
            "price_range": self.price_range(),
        }


# ========== mock data ==========

_MOCK_PRODUCTS: list[Product] = [
    Product("B001", "Halloween Garland LED Decor", "halloween garland", 15.99, 234, 4.5, "Decor", 520),
    Product("B002", "Halloween Pumpkin Garland 6ft", "halloween garland", 22.50, 89, 3.8, "Decor", 180),
    Product("B003", "Halloween Spider Web Garland Set", "halloween garland", 18.99, 456, 4.7, "Decor", 890),
    Product("B004", "Halloween LED String Lights Purple", "halloween garland", 12.99, 567, 4.3, "Lights", 1200),
    Product("B005", "Halloween Door Garland Deluxe", "halloween garland", 35.00, 67, 4.1, "Decor", 95),
    Product("B006", "Halloween Ghost Garland Cute", "halloween garland", 9.99, 789, 4.6, "Decor", 1500),
    Product("B007", "Halloween Bat Garland Black", "halloween garland", 14.50, 123, 4.0, "Decor", 310),
    Product("B008", "Halloween Skull Garland Horror", "halloween garland", 28.00, 45, 3.5, "Decor", 42),
    Product("B009", "Halloween Orange Berry Garland", "halloween garland", 19.99, 312, 4.4, "Decor", 670),
    Product("B010", "Halloween Wizard Theme Garland", "halloween garland", 42.00, 23, 3.2, "Decor", 28),
    Product("B011", "Halloween Mini Garland 6-Pack", "halloween garland", 8.50, 891, 4.8, "Decor", 2100),
    Product("B012", "Halloween Glow Skull Garland", "halloween garland", 55.00, 12, 2.8, "Premium", 15),
    Product("B013", "Bluetooth Noise Cancelling Headphones Pro", "bluetooth headphone", 79.99, 2340, 4.4, "Electronics", 3200),
    Product("B014", "Wireless Bluetooth Earbuds Sport", "bluetooth headphone", 29.99, 5670, 4.2, "Electronics", 8900),
    Product("B015", "Over-Ear Bluetooth Headphones Bass", "bluetooth headphone", 49.99, 1230, 4.6, "Electronics", 2100),
    Product("B016", "Bluetooth Sleep Headphones Ultra-Thin", "bluetooth headphone", 19.99, 890, 3.9, "Electronics", 1500),
    Product("B017", "Kids Bluetooth Headphones Volume Limit", "bluetooth headphone", 24.99, 450, 4.3, "Electronics", 780),
    Product("B018", "HiFi Bluetooth Headphones Audiophile", "bluetooth headphone", 199.99, 340, 4.7, "Electronics", 450),
    Product("B019", "Waterproof Bluetooth Earphones IPX7", "bluetooth headphone", 39.99, 1670, 4.1, "Electronics", 2600),
    Product("B020", "Retro Bluetooth Headphones Wood", "bluetooth headphone", 89.99, 210, 4.0, "Electronics", 320),
]


class ProductRepository:
    """Data access — returns ProductCollection, no business logic."""

    def __init__(self):
        self._products: list[Product] = list(_MOCK_PRODUCTS)

    def get_all(self) -> ProductCollection:
        """Return all products."""
        return ProductCollection(list(self._products))

    def search_by_keyword(self, keyword: str) -> ProductCollection:
        """Fuzzy-search products by keyword (matches against title + keyword fields)."""
        keyword_lower = keyword.lower()
        matched = [
            p for p in self._products
            if keyword_lower in p.keyword.lower()
            or keyword_lower in p.title.lower()
        ]
        return ProductCollection(matched)

    def search_by_category(self, category: str) -> ProductCollection:
        """Exact-match search by category."""
        matched = [p for p in self._products if p.category == category]
        return ProductCollection(matched)
