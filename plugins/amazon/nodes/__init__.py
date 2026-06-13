"""Amazon plugin — Node definitions

Nodes are organized by function, not by a type label:
  - source_nodes:     data fetching (no inputs, graph entry points)
  - transform_nodes:  data filtering/sorting (ProductCollection → ProductCollection)
  - sink_nodes:       analysis, aggregation, and formatted output

Every Node follows the same pattern: unpack Artifact → call Service → pack result.
See plugins/amazon/services/ for the business logic these nodes delegate to.
"""
