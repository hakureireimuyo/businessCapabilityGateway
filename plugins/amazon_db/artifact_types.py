"""Amazon DB plugin — Artifact type hierarchy

All types inherit from ArtifactType. Type compatibility uses issubclass:
a subtype can flow into any input that expects a supertype.
"""

from core.protocol.artifact import ArtifactType


# ---- Raw Data ----

class ProductCollection(ArtifactType):
    """Collection of products (raw data from search)."""
    pass


class FilteredProductCollection(ProductCollection):
    """Filtered subset of products."""
    pass


# ---- Metrics ----

class SalesMetrics(ArtifactType):
    """Sales statistical analysis result."""
    pass


class ReviewMetrics(ArtifactType):
    """Review statistical analysis result."""
    pass


# ---- Analysis (aggregated, high-dimension semantics) ----

class MarketAnalysis(ArtifactType):
    """Market analysis result (size, price, competition)."""
    pass


class CompetitionAnalysis(ArtifactType):
    """Competition landscape assessment."""
    pass


# ---- Aggregated Summaries ----
# These types enforce the "high-dimension semantics" boundary principle:
# output must be Agent-reasoning-ready aggregates, never raw per-item lists.

class OpportunitySummary(ArtifactType):
    """Aggregated opportunity analysis: summary stats + top N opportunities."""
    pass


class ScoringSummary(ArtifactType):
    """Aggregated product scoring: score distribution + top N products."""
    pass


class DiagnosisSummary(ArtifactType):
    """Aggregated product diagnosis: category counts + top N per category."""
    pass


class KeywordMarketSummary(ArtifactType):
    """Aggregated keyword market analysis: size distribution + top N keywords."""
    pass


class KeywordCompetitionSummary(ArtifactType):
    """Aggregated keyword competition analysis: level distribution + top N keywords."""
    pass


class KeywordMarginSummary(ArtifactType):
    """Aggregated keyword margin analysis: high-margin count + top N keywords."""
    pass


class KeywordTrendSummary(ArtifactType):
    """Aggregated keyword trend analysis: trend distribution + growing/declining keywords."""
    pass


# ---- Aggregations ----

class MarketSignal(ArtifactType):
    """Aggregated market signal from multiple metrics."""
    pass


# ---- Output ----

class ChartData(ArtifactType):
    """Chart visualization data."""
    pass


class JSONData(ArtifactType):
    """Raw JSON output."""
    pass
