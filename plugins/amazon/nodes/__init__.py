"""Amazon plugin — Node definitions

Nodes are organized by function, not by a type label:
  - source_nodes: Data fetching (no inputs)
  - transform_nodes: Data filtering/sorting (ProductCollection → ProductCollection)
  - sink_nodes: Analysis & output (ProductCollection → metrics/aggregations)
"""
