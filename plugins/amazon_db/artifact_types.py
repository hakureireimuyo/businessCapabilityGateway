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


# ---- Analysis ----

class MarketAnalysis(ArtifactType):
    """Market analysis result (size, price, competition)."""
    pass


class OpportunityList(ArtifactType):
    """List of identified market opportunities."""
    pass


class CompetitionAnalysis(ArtifactType):
    """Competition landscape assessment."""
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
