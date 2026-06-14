"""Tag Alignment Plugin — Artifact type hierarchy.

All types inherit from ArtifactType. Type compatibility uses issubclass:
a subtype can flow into any input that expects a supertype.
"""

from core.protocol.artifact import ArtifactType


class TagCandidateSet(ArtifactType):
    """A collection of tag candidates for a single token.

    Contains the original token and its top-3 matching tags (by count DESC).
    """
    pass


class SearchRequestSet(ArtifactType):
    """A set of search URL requests produced by the URL conversion layer.

    Each entry is a flat tag-group with an encoded URL.
    """
    pass
