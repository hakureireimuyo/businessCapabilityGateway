"""Amazon DB plugin — business service layer

All business logic (statistics, scoring, analysis algorithms) lives here.
Services receive ProductCollection (plain Python objects) and return plain dicts.
They know nothing about Artifacts or the Node layer.

See plugins/amazon_db/nodes/ for the Node layer that calls these services.
"""

from plugins.amazon_db.repository.product_repository import ProductCollection


class MarketService:
    """Statistical analysis and scoring for Amazon product data."""

    # ---- market analysis ----

    @staticmethod
    def analyze_market(products: ProductCollection) -> dict:
        """Compute market statistics: size, avg price, competition score (0-100),
        sales distribution, margin stats.
        """
        if len(products) == 0:
            return {
                "market_size": 0,
                "avg_price": 0.0,
                "avg_rating": 0.0,
                "avg_margin": 0.0,
                "competition_score": 0,
                "total_monthly_sales": 0,
                "total_sales_amount": 0.0,
                "price_range": [0, 0],
            }

        seller_count = len(products)
        total_reviews = sum(p.review_count for p in products)
        avg_reviews = total_reviews / seller_count if seller_count > 0 else 0

        # Competition score 0-100: higher = more competitive
        if seller_count <= 3:
            competition_score = 15
        elif avg_reviews < 100:
            competition_score = 25
        elif avg_reviews < 500:
            competition_score = 50
        elif avg_reviews < 1000:
            competition_score = 70
        else:
            competition_score = 90

        # If many low-review sellers, treat as blue ocean
        low_review_count = sum(1 for p in products if p.review_count < 100)
        if low_review_count / max(seller_count, 1) > 0.5:
            competition_score = max(10, competition_score - 20)

        price_min, price_max = products.price_range()

        return {
            "market_size": seller_count,
            "avg_price": products.avg_price(),
            "avg_rating": products.avg_rating(),
            "avg_margin": products.avg_margin(),
            "competition_score": min(100, competition_score),
            "total_monthly_sales": products.total_sales(),
            "total_sales_amount": products.total_sales_amount(),
            "price_range": [price_min, price_max],
        }

    @staticmethod
    def find_opportunities(products: ProductCollection, max_review: int = 100) -> dict:
        """Find low-competition, high-opportunity products based on review count and rating."""
        if len(products) == 0:
            return {"opportunity_count": 0, "opportunities": []}

        opportunities = []
        for p in products:
            if p.review_count < max_review:
                opportunity_score = min(100, int(
                    (p.rating / 5.0) * 40 +
                    (min(p.monthly_sales, 2000) / 2000) * 40 +
                    (1 - p.review_count / max(max_review, 1)) * 20
                ))
                if opportunity_score > 30:
                    opportunities.append({
                        "asin": p.asin,
                        "title": p.title,
                        "price": p.price,
                        "review_count": p.review_count,
                        "rating": p.rating,
                        "monthly_sales": p.monthly_sales,
                        "gross_margin": p.gross_margin,
                        "opportunity_score": opportunity_score,
                    })

        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return {
            "opportunity_count": len(opportunities),
            "opportunities": opportunities[:10],
        }

    @staticmethod
    def competition_analysis(products: ProductCollection) -> dict:
        """Assess competition landscape: high/low-end distribution, dominant players,
        entry barrier score.
        """
        if len(products) == 0:
            return {
                "total_competitors": 0,
                "high_end_count": 0,
                "low_end_count": 0,
                "avg_price": 0.0,
                "avg_rating": 0.0,
                "dominant_players": 0,
                "entry_barrier_score": 0,
            }

        total = len(products)
        avg_price = products.avg_price()

        # High-end: price > 1.5x average
        high_end = sum(1 for p in products if p.price > avg_price * 1.5)
        # Low-end: price < 0.5x average
        low_end = sum(1 for p in products if p.price < avg_price * 0.5)

        # Dominant players: review_count > 1000
        dominant = sum(1 for p in products if p.review_count > 1000)

        # Entry barrier score 0-100, higher = harder to enter
        barrier = min(100, int(
            (dominant / max(total, 1)) * 50 +
            (avg_price / 100) * 30 +
            (1 - low_end / max(total, 1)) * 20
        ))

        return {
            "total_competitors": total,
            "high_end_count": high_end,
            "low_end_count": low_end,
            "avg_price": avg_price,
            "avg_rating": products.avg_rating(),
            "dominant_players": dominant,
            "entry_barrier_score": barrier,
        }

    # ---- sales analysis ----

    @staticmethod
    def analyze_sales(products: ProductCollection) -> dict:
        """Compute sales statistics: total, avg, max, product count, plus revenue data."""
        if len(products) == 0:
            return {
                "total_sales": 0, "avg_sales": 0.0, "max_sales": 0,
                "total_sales_amount": 0.0, "avg_sales_amount": 0.0,
                "product_count": 0,
            }

        sales_values = [p.monthly_sales for p in products]
        amount_values = [p.sales_amount for p in products]
        return {
            "total_sales": sum(sales_values),
            "avg_sales": round(sum(sales_values) / len(sales_values), 1),
            "max_sales": max(sales_values),
            "total_sales_amount": round(sum(amount_values), 2),
            "avg_sales_amount": round(sum(amount_values) / len(amount_values), 2),
            "product_count": len(products),
        }

    # ---- review analysis ----

    @staticmethod
    def analyze_reviews(products: ProductCollection) -> dict:
        """Compute review statistics: avg rating, total reviews, avg per product."""
        if len(products) == 0:
            return {
                "avg_rating": 0.0, "total_reviews": 0,
                "avg_reviews": 0.0, "product_count": 0,
            }

        ratings = [p.rating for p in products]
        reviews = [p.review_count for p in products]
        return {
            "avg_rating": round(sum(ratings) / len(ratings), 2),
            "total_reviews": sum(reviews),
            "avg_reviews": round(sum(reviews) / len(reviews), 1),
            "product_count": len(products),
        }

    # ---- market score ----

    @staticmethod
    def compute_market_score(
        sales_data: dict, review_data: dict, method: str = "weighted"
    ) -> dict:
        """Aggregate sales and review metrics into a composite market signal (0-100)."""
        total_sales = sales_data.get("total_sales", 0)
        avg_rating = review_data.get("avg_rating", 0)
        product_count = sales_data.get("product_count", 0)

        sales_normalized = min(100, int(total_sales / 100)) if total_sales > 0 else 0
        rating_normalized = int(avg_rating / 5.0 * 100) if avg_rating > 0 else 0

        if method == "simple":
            signal = int((sales_normalized + rating_normalized) / 2)
        else:
            signal = int(sales_normalized * 0.4 + rating_normalized * 0.6)

        return {
            "market_signal_score": signal,
            "sales_contribution": sales_normalized,
            "rating_contribution": rating_normalized,
            "product_count": product_count,
            "method": method,
        }
