"""Amazon DB plugin — business service layer

All business logic (statistics, scoring, analysis algorithms) lives here.
Services receive ProductCollection (plain Python objects) and return plain dicts.
They know nothing about Artifacts or the Node layer.

All analysis methods enforce the "high-dimension semantics" boundary principle:
outputs are aggregated summaries + top-N highlights, never raw per-item lists.

See plugins/amazon_db/nodes/ for the Node layer that calls these services.
"""

from datetime import date

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
    def find_opportunities(products: ProductCollection, max_review: int = 100,
                           top_n: int = 10) -> dict:
        """Find low-competition, high-opportunity products.

        Returns an aggregated summary — never raw product lists.
        """
        total_scanned = len(products)
        if total_scanned == 0:
            return {
                "summary": {
                    "total_scanned": 0,
                    "opportunity_count": 0,
                    "avg_opportunity_score": 0.0,
                    "avg_price": 0.0,
                    "avg_margin": 0.0,
                },
                "top_opportunities": [],
            }

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
                        "title": p.title[:80] if p.title else "",
                        "opportunity_score": opportunity_score,
                        "price": p.price,
                        "gross_margin": round(p.gross_margin * 100, 1),
                    })

        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
        opp_count = len(opportunities)
        top_items = opportunities[:top_n]

        # Compute summary stats
        if opp_count > 0:
            avg_score = round(sum(o["opportunity_score"] for o in opportunities) / opp_count, 1)
            avg_price = round(sum(o["price"] for o in opportunities) / opp_count, 2)
            avg_margin = round(sum(o["gross_margin"] for o in opportunities) / opp_count, 1)
        else:
            avg_score = 0.0
            avg_price = 0.0
            avg_margin = 0.0

        return {
            "summary": {
                "total_scanned": total_scanned,
                "opportunity_count": opp_count,
                "avg_opportunity_score": avg_score,
                "avg_price": avg_price,
                "avg_margin": avg_margin,
            },
            "top_opportunities": top_items,
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

    # ---- product scoring (aggregated) ----

    @staticmethod
    def score_products(
        products: ProductCollection,
        weight_profit: float = 0.40,
        weight_competition: float = 0.30,
        weight_quality: float = 0.20,
        weight_freshness: float = 0.10,
        top_n: int = 10,
    ) -> dict:
        """Score products on 4 dimensions using percentile ranking within keyword group.

        Returns an aggregated summary (score distribution + top N), never raw per-item lists.
        """
        if len(products) == 0:
            return {
                "summary": {
                    "total_products": 0,
                    "avg_total_score": 0.0,
                    "median_total_score": 0.0,
                    "score_distribution": {
                        "excellent": 0, "good": 0, "average": 0, "poor": 0,
                    },
                },
                "top_products": [],
            }

        # Group products by keyword
        from collections import defaultdict
        kw_groups: dict[str, list] = defaultdict(list)
        for p in products:
            kw_groups[p.keyword or "(unknown)"].append(p)

        all_scored = []

        for kw, prods in kw_groups.items():
            n = len(prods)
            if n < 2:
                for p in prods:
                    all_scored.append({
                        "keyword": kw,
                        "asin": p.asin,
                        "title": p.title[:80] if p.title else "",
                        "profit_score": 50.0,
                        "competition_score": 50.0,
                        "quality_score": 50.0,
                        "freshness_score": 50.0,
                        "total_score": 50.0,
                    })
                continue

            margins = sorted(p.gross_margin for p in prods)
            reviews = sorted(p.review_count for p in prods)
            ratings = sorted(p.rating for p in prods)
            days_list = sorted(p.launch_days for p in prods)

            for p in prods:
                profit_rank = MarketService._percentile_rank(margins, p.gross_margin)
                competition_rank = 1.0 - MarketService._percentile_rank(reviews, p.review_count)
                quality_rank = MarketService._percentile_rank(ratings, p.rating)
                freshness_rank = 1.0 - MarketService._percentile_rank(days_list, p.launch_days)

                total = round(
                    profit_rank * 100 * weight_profit
                    + competition_rank * 100 * weight_competition
                    + quality_rank * 100 * weight_quality
                    + freshness_rank * 100 * weight_freshness,
                    1,
                )

                all_scored.append({
                    "keyword": kw,
                    "asin": p.asin,
                    "title": p.title[:80] if p.title else "",
                    "profit_score": round(profit_rank * 100, 1),
                    "competition_score": round(competition_rank * 100, 1),
                    "quality_score": round(quality_rank * 100, 1),
                    "freshness_score": round(freshness_rank * 100, 1),
                    "total_score": total,
                })

        # Sort by total_score descending
        all_scored.sort(key=lambda x: -x["total_score"])

        # --- Compute summary ---
        total = len(all_scored)
        scores = [s["total_score"] for s in all_scored]
        avg_score = round(sum(scores) / total, 1)
        median_score = round(MarketService._median_value(scores), 1) if scores else 0.0

        excellent = sum(1 for s in scores if s >= 80)
        good = sum(1 for s in scores if 60 <= s < 80)
        average = sum(1 for s in scores if 40 <= s < 60)
        poor = sum(1 for s in scores if s < 40)

        return {
            "summary": {
                "total_products": total,
                "avg_total_score": avg_score,
                "median_total_score": median_score,
                "score_distribution": {
                    "excellent": excellent,
                    "good": good,
                    "average": average,
                    "poor": poor,
                },
            },
            "top_products": all_scored[:top_n],
        }

    @staticmethod
    def _percentile_rank(sorted_vals: list, target: float) -> float:
        """Compute percentile rank (0.0–1.0) of target within sorted_vals."""
        if not sorted_vals:
            return 0.5
        n = len(sorted_vals)
        lt = sum(1 for v in sorted_vals if v < target)
        eq = sum(1 for v in sorted_vals if v == target)
        return (lt + eq * 0.5) / n

    @staticmethod
    def _median_value(sorted_vals: list) -> float | None:
        """Compute median of a list of numbers (already sorted)."""
        if not sorted_vals:
            return None
        n = len(sorted_vals)
        if n % 2 == 1:
            return float(sorted_vals[n // 2])
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    # ---- product diagnosis (aggregated) ----

    @staticmethod
    def diagnose_products(products: ProductCollection, top_n: int = 10) -> dict:
        """Comprehensive product diagnosis: flags promising new products,
        declining old products, and rating/review anomalies.

        Returns aggregated summary by diagnosis type + top N per category.
        """
        if len(products) == 0:
            return {
                "summary": {
                    "total_diagnosed": 0,
                    "promising_new": 0,
                    "declining": 0,
                    "potential_star": 0,
                    "reputation_crisis": 0,
                },
                "top_promising": [],
                "top_declining": [],
                "top_potential_star": [],
                "top_reputation_crisis": [],
            }

        from collections import defaultdict
        kw_groups: dict[str, list] = defaultdict(list)
        for p in products:
            kw_groups[p.keyword or "(unknown)"].append(p)

        results = []

        for kw, prods in kw_groups.items():
            reviews_list = sorted(p.review_count for p in prods)
            ratings_list = [p.rating for p in prods if p.rating > 0]
            kw_avg_reviews = sum(reviews_list) / len(reviews_list) if reviews_list else 0
            kw_avg_rating = sum(ratings_list) / len(ratings_list) if ratings_list else 4.0
            n = len(reviews_list)
            review_p70 = reviews_list[int(n * 0.7)] if n >= 3 else 0

            rates = []
            for p in prods:
                if p.launch_days and p.launch_days > 0:
                    rates.append(p.review_count / p.launch_days)
            kw_avg_rate = sum(rates) / len(rates) if rates else 0

            for p in prods:
                diagnosis_type = "normal"

                is_new = p.launch_days is not None and 0 < p.launch_days < 365
                review_top30 = p.review_count >= review_p70 if review_p70 > 0 else False
                rating_good = p.rating is not None and p.rating >= 4.0
                is_promising = is_new and review_top30 and rating_good

                is_old = p.launch_days is not None and p.launch_days > 730
                declining = False
                if is_old:
                    decline_score = 0
                    rate = p.review_count / p.launch_days if p.launch_days > 0 else 0
                    if kw_avg_rate > 0 and rate < kw_avg_rate * 0.7:
                        decline_score += 1
                    if p.parent_category_rank > 50000:
                        decline_score += 1
                    if p.sub_category_rank > 1000:
                        decline_score += 1
                    if decline_score >= 2:
                        diagnosis_type = "declining"
                        declining = True

                if not declining and p.rating is not None and p.rating > 0:
                    high_rating = p.rating >= (kw_avg_rating + 0.5)
                    low_reviews = p.review_count < kw_avg_reviews * 0.5
                    low_rating = p.rating <= (kw_avg_rating - 0.5)
                    high_reviews = p.review_count > kw_avg_reviews

                    if high_rating and low_reviews:
                        diagnosis_type = "potential_star"
                    elif low_rating and high_reviews:
                        diagnosis_type = "reputation_crisis"

                if is_promising:
                    diagnosis_type = "promising_new"

                results.append({
                    "keyword": kw,
                    "asin": p.asin,
                    "title": p.title[:80] if p.title else "",
                    "diagnosis_type": diagnosis_type,
                    "review_count": p.review_count,
                    "rating": p.rating,
                    "launch_days": p.launch_days,
                    "gross_margin": round(p.gross_margin * 100, 1),
                    "price": p.price,
                })

        # --- Categorize and sort ---
        promising = sorted(
            [r for r in results if r["diagnosis_type"] == "promising_new"],
            key=lambda x: -x["review_count"],
        )
        declining = sorted(
            [r for r in results if r["diagnosis_type"] == "declining"],
            key=lambda x: x["review_count"],
        )
        potential_star = sorted(
            [r for r in results if r["diagnosis_type"] == "potential_star"],
            key=lambda x: -x["rating"] if x["rating"] else 0,
        )
        reputation_crisis = sorted(
            [r for r in results if r["diagnosis_type"] == "reputation_crisis"],
            key=lambda x: -x["review_count"],
        )

        return {
            "summary": {
                "total_diagnosed": len(results),
                "promising_new": len(promising),
                "declining": len(declining),
                "potential_star": len(potential_star),
                "reputation_crisis": len(reputation_crisis),
            },
            "top_promising": promising[:top_n],
            "top_declining": declining[:top_n],
            "top_potential_star": potential_star[:top_n],
            "top_reputation_crisis": reputation_crisis[:top_n],
        }


# ================================================================
# KeywordAnalysisService — keyword-level aggregation analysis
# ================================================================

class KeywordAnalysisService:
    """Statistical analysis on per-keyword aggregated data.

    Receives list[dict] from KeywordRepository aggregation methods and
    performs Python-level statistical computation. All output methods
    return aggregated summaries + top-N highlights, never raw per-keyword lists.
    """

    # ---- keyword market analysis ----

    @staticmethod
    def analyze_keyword_market(stats_list: list[dict], top_n: int = 10) -> dict:
        """Aggregate keyword market stats into summary + top N markets.

        Returns summary with market-size distribution, monopoly count,
        and top markets sorted by total_reviews descending.
        """
        if not stats_list:
            return {
                "summary": {
                    "total_keywords": 0,
                    "total_products": 0,
                    "total_reviews": 0,
                    "market_size_distribution": {
                        "大型市场": 0, "中型市场": 0, "小型市场": 0, "小众市场": 0,
                    },
                    "monopoly_keyword_count": 0,
                },
                "top_markets": [],
            }

        enriched = []
        total_products = 0
        total_reviews = 0
        size_dist = {"大型市场": 0, "中型市场": 0, "小型市场": 0, "小众市场": 0}
        monopoly_count = 0

        for entry in stats_list:
            kw = entry["keyword"]
            product_count = entry["product_count"]
            tr = entry["total_reviews"]
            review_values = entry.get("review_values", [])

            median = KeywordAnalysisService._median(review_values)

            top3_sum = sum(review_values[-3:]) if len(review_values) >= 3 else tr
            top3_share = round(top3_sum / tr, 4) if tr > 0 else None
            is_monopoly = (top3_share or 0) > 0.6

            if tr > 50000:
                size_label = "大型市场"
            elif tr > 10000:
                size_label = "中型市场"
            elif tr > 2000:
                size_label = "小型市场"
            else:
                size_label = "小众市场"

            total_products += product_count
            total_reviews += tr
            size_dist[size_label] += 1
            if is_monopoly:
                monopoly_count += 1

            enriched.append({
                "keyword": kw,
                "product_count": product_count,
                "total_reviews": tr,
                "avg_reviews": (
                    round(tr / product_count, 2) if product_count > 0 else 0.0
                ),
                "median_reviews": round(median, 2) if median is not None else None,
                "top3_review_share": top3_share,
                "top3_is_monopoly": is_monopoly,
                "market_size_label": size_label,
            })

        enriched.sort(key=lambda x: x["total_reviews"], reverse=True)

        return {
            "summary": {
                "total_keywords": len(enriched),
                "total_products": total_products,
                "total_reviews": total_reviews,
                "market_size_distribution": size_dist,
                "monopoly_keyword_count": monopoly_count,
            },
            "top_markets": enriched[:top_n],
        }

    # ---- keyword competition analysis ----

    @staticmethod
    def analyze_keyword_competition(stats_list: list[dict], top_n: int = 10) -> dict:
        """Aggregate keyword competition stats into summary + top N keywords.

        Returns competition-level distribution, avg Gini & new-product ratio,
        and top keywords (blue-ocean first, then by product count).
        """
        if not stats_list:
            return {
                "summary": {
                    "total_keywords": 0,
                    "competition_distribution": {
                        "蓝海": 0, "中等竞争": 0, "红海（头部垄断）": 0, "红海": 0,
                    },
                    "avg_review_gini": 0.0,
                    "avg_new_product_ratio": 0.0,
                },
                "top_keywords": [],
            }

        enriched = []
        ginis = []
        new_ratios = []
        comp_dist = {"蓝海": 0, "中等竞争": 0, "红海（头部垄断）": 0, "红海": 0}

        for entry in stats_list:
            kw = entry["keyword"]
            product_count = entry["product_count"]
            avg_reviews = entry["avg_reviews"]
            review_values = entry.get("review_values", [])
            launch_dates = entry.get("launch_dates", [])

            gini = KeywordAnalysisService._gini(review_values)
            std = KeywordAnalysisService._std(review_values)
            cv = round(std / avg_reviews, 4) if avg_reviews and std else None

            one_year_ago = date.today().replace(year=date.today().year - 1)
            new_count = sum(1 for d in launch_dates if d >= one_year_ago)
            new_ratio = round(new_count / product_count, 4) if product_count > 0 else None

            if product_count <= 10 and (gini or 0) < 0.4:
                level = "蓝海"
            elif product_count <= 30 and (gini or 0) < 0.5:
                level = "中等竞争"
            elif (gini or 0) > 0.7:
                level = "红海（头部垄断）"
            else:
                level = "红海"

            comp_dist[level] += 1
            if gini is not None:
                ginis.append(gini)
            if new_ratio is not None:
                new_ratios.append(new_ratio)

            enriched.append({
                "keyword": kw,
                "product_count": product_count,
                "review_gini": round(gini, 4) if gini is not None else None,
                "review_cv": cv,
                "new_product_ratio": new_ratio,
                "competition_level": level,
            })

        # Sort: blue ocean first, then medium, then red ocean
        level_order = {"蓝海": 0, "中等竞争": 1, "红海": 2, "红海（头部垄断）": 3}
        enriched.sort(key=lambda x: (level_order.get(x["competition_level"], 9), x["product_count"]))

        avg_gini = round(sum(ginis) / len(ginis), 4) if ginis else 0.0
        avg_new = round(sum(new_ratios) / len(new_ratios), 4) if new_ratios else 0.0

        return {
            "summary": {
                "total_keywords": len(enriched),
                "competition_distribution": comp_dist,
                "avg_review_gini": avg_gini,
                "avg_new_product_ratio": avg_new,
            },
            "top_keywords": enriched[:top_n],
        }

    # ---- keyword margin analysis ----

    @staticmethod
    def analyze_keyword_margin(stats_list: list[dict], top_n: int = 10) -> dict:
        """Aggregate keyword margin stats into summary + top N high-margin keywords.

        Returns high-margin count, overall avg/median margin, and top keywords
        sorted by avg margin descending.
        """
        if not stats_list:
            return {
                "summary": {
                    "total_keywords": 0,
                    "high_margin_count": 0,
                    "overall_avg_margin": 0.0,
                    "overall_median_margin": 0.0,
                },
                "top_margin_keywords": [],
            }

        enriched = []
        all_avg_margins = []
        high_margin_count = 0

        for entry in stats_list:
            kw = entry["keyword"]
            product_count = entry["product_count"]
            margin_values = entry.get("margin_values", [])

            median = KeywordAnalysisService._median(margin_values)
            q25, q75 = KeywordAnalysisService._quartiles(margin_values)
            avg_margin = entry.get("avg_margin", 0.0)
            is_high = avg_margin > 0.4

            all_avg_margins.append(avg_margin)
            if is_high:
                high_margin_count += 1

            enriched.append({
                "keyword": kw,
                "product_count": product_count,
                "avg_gross_margin": round(avg_margin * 100, 1),
                "median_gross_margin": round(median * 100, 1) if median is not None else None,
                "q25_gross_margin": round(q25 * 100, 1) if q25 is not None else None,
                "q75_gross_margin": round(q75 * 100, 1) if q75 is not None else None,
                "min_gross_margin": round(entry.get("min_margin", 0.0) * 100, 1),
                "max_gross_margin": round(entry.get("max_margin", 0.0) * 100, 1),
                "is_high_margin": is_high,
            })

        enriched.sort(key=lambda x: x["avg_gross_margin"] or 0, reverse=True)

        overall_avg = round(sum(all_avg_margins) / len(all_avg_margins) * 100, 1) if all_avg_margins else 0.0
        overall_median = round(
            KeywordAnalysisService._median(sorted(all_avg_margins)) * 100, 1
        ) if all_avg_margins else 0.0

        return {
            "summary": {
                "total_keywords": len(enriched),
                "high_margin_count": high_margin_count,
                "overall_avg_margin": overall_avg,
                "overall_median_margin": overall_median,
            },
            "top_margin_keywords": enriched[:top_n],
        }

    # ---- keyword launch trend analysis ----

    @staticmethod
    def analyze_keyword_trend(stats_list: list[dict], top_n: int = 10) -> dict:
        """Aggregate keyword trend stats into summary + growing/declining keywords.

        Returns trend distribution, and separate lists for growing and
        declining keywords (each capped at top_n).
        """
        if not stats_list:
            return {
                "summary": {
                    "total_keywords": 0,
                    "trend_distribution": {
                        "增长期": 0, "稳定期": 0, "可能衰退": 0, "无数据": 0,
                    },
                },
                "growing_keywords": [],
                "declining_keywords": [],
            }

        trend_dist = {"增长期": 0, "稳定期": 0, "可能衰退": 0, "无数据": 0}
        growing = []
        declining = []

        for entry in stats_list:
            total = entry.get("total_products", 0)
            recent = entry.get("products_2025", 0) + entry.get("products_2026", 0)
            older = total - recent

            if total == 0:
                trend = "无数据"
            elif recent > older and total > 5:
                trend = "增长期"
            elif older > 0 and recent < older * 0.3:
                trend = "可能衰退"
            else:
                trend = "稳定期"

            trend_dist[trend] += 1

            enriched = {
                "keyword": entry["keyword"],
                "total_products": total,
                "products_2025": entry.get("products_2025", 0),
                "products_2026": entry.get("products_2026", 0),
                "trend": trend,
            }

            if trend == "增长期":
                growing.append(enriched)
            elif trend == "可能衰退":
                declining.append(enriched)

        growing.sort(key=lambda x: -x["total_products"])
        declining.sort(key=lambda x: -x["total_products"])

        return {
            "summary": {
                "total_keywords": len(stats_list),
                "trend_distribution": trend_dist,
            },
            "growing_keywords": growing[:top_n],
            "declining_keywords": declining[:top_n],
        }

    # ---- statistical helpers ----

    @staticmethod
    def _median(sorted_vals: list) -> float | None:
        if not sorted_vals:
            return None
        n = len(sorted_vals)
        if n % 2 == 1:
            return float(sorted_vals[n // 2])
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    @staticmethod
    def _quartiles(sorted_vals: list) -> tuple[float | None, float | None]:
        if not sorted_vals or len(sorted_vals) < 4:
            return None, None
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]
        return float(q1), float(q3)

    @staticmethod
    def _std(vals: list) -> float | None:
        if not vals:
            return None
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        return variance ** 0.5

    @staticmethod
    def _gini(sorted_vals: list) -> float | None:
        if not sorted_vals:
            return None
        n = len(sorted_vals)
        total = sum(sorted_vals)
        if total == 0:
            return 0.0
        weighted_sum = sum((i + 1) * v for i, v in enumerate(sorted_vals))
        gini = (2 * weighted_sum) / (n * total) - (n + 1) / n
        return gini
