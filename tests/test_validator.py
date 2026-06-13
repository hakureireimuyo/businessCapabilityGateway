"""Unit tests for GraphValidator — 7-layer graph validation"""
import unittest
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph.model import Graph, GraphNode, GraphEdge
from core.graph.validator import GraphValidator
from core.registry.node_registry import get_registry
from core.plugin.loader import discover_and_load_plugins


class TestGraphValidator(unittest.TestCase):
    """Tests for the GraphValidator's 7 validation layers."""

    @classmethod
    def setUpClass(cls):
        """Load plugins once for all tests."""
        discover_and_load_plugins()

    def setUp(self):
        self.validator = GraphValidator()
        self.registry = get_registry()

    # ---- Layer 1: Node existence ----

    def test_valid_two_node_graph(self):
        """keyword_search → market_analysis: should be valid."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ks": GraphNode(node_id="ks", node_name="keyword_search",
                                params={"keyword": "test"}),
                "ma": GraphNode(node_id="ma", node_name="market_analysis"),
            },
            edges=[
                GraphEdge(from_node="ks", from_output="products",
                          to_node="ma", to_input="products"),
            ],
            outputs=["ma"],
        )
        errors = self.validator.validate(g)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_node_not_found(self):
        """Non-existent node name should be caught at layer 1."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ghost": GraphNode(node_id="ghost", node_name="ghost_node"),
            },
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(e["layer"] == "NODE_NOT_FOUND" for e in errors))

    def test_plugin_not_found(self):
        """Non-existent plugin should be caught at layer 1."""
        g = Graph(
            plugin="nonexistent",
            nodes={
                "n": GraphNode(node_id="n", node_name="keyword_search"),
            },
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(e["layer"] == "NODE_NOT_FOUND" for e in errors))

    # ---- Layer 2: Parameter validity ----

    def test_missing_required_param(self):
        """keyword_search requires 'keyword' param — missing should be caught."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ks": GraphNode(node_id="ks", node_name="keyword_search"),
            },
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(
            e["layer"] == "INVALID_PARAMS" and "keyword" in str(e)
            for e in errors
        ))

    def test_unknown_param(self):
        """Non-existent parameter should be caught."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ks": GraphNode(node_id="ks", node_name="keyword_search",
                                params={"keyword": "test", "ghost_param": 123}),
            },
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(
            e["layer"] == "INVALID_PARAMS" and "ghost_param" in str(e)
            for e in errors
        ))

    def test_param_type_mismatch(self):
        """keyword expects str, passing int should be caught."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ks": GraphNode(node_id="ks", node_name="keyword_search",
                                params={"keyword": 12345}),
            },
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(e["layer"] == "INVALID_PARAMS" for e in errors))

    # ---- Layer 3: Input completeness ----

    def test_unsatisfied_input(self):
        """market_analysis requires 'products' input — missing edge should be caught."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ma": GraphNode(node_id="ma", node_name="market_analysis"),
            },
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(
            e["layer"] == "UNSATISFIED_INPUT" and "products" in str(e)
            for e in errors
        ))

    def test_satisfied_input(self):
        """keyword_search has no inputs — should be valid without edges."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ks": GraphNode(node_id="ks", node_name="keyword_search",
                                params={"keyword": "test"}),
            },
            outputs=["ks"],
        )
        errors = self.validator.validate(g)
        self.assertEqual(errors, [])

    # ---- Layer 4: Type compatibility ----

    def test_type_mismatch(self):
        """Feeding MarketAnalysis output into sales_analysis 'products' input
        should be caught — ProductCollection ≠ MarketAnalysis."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ma": GraphNode(node_id="ma", node_name="market_analysis"),
                "sa": GraphNode(node_id="sa", node_name="sales_analysis"),
            },
            edges=[
                GraphEdge(from_node="ma", from_output="market_analysis",
                          to_node="sa", to_input="products"),
            ],
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(e["layer"] == "TYPE_MISMATCH" for e in errors))

    # ---- Layer 5: Cycle detection ----

    def test_cycle_detection(self):
        """A → B → A should be caught as cyclic."""
        g = Graph(
            plugin="amazon",
            nodes={
                "a": GraphNode(node_id="a", node_name="keyword_search",
                               params={"keyword": "test"}),
                "b": GraphNode(node_id="b", node_name="filter"),
            },
            edges=[
                GraphEdge(from_node="a", from_output="products",
                          to_node="b", to_input="products"),
                GraphEdge(from_node="b", from_output="filtered_products",
                          to_node="a", to_input="products"),
            ],
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(e["layer"] == "CYCLIC_DEPENDENCY" for e in errors))

    def test_dag_no_cycle(self):
        """A → B → C (chain) should pass cycle check."""
        g = Graph(
            plugin="amazon",
            nodes={
                "a": GraphNode(node_id="a", node_name="keyword_search",
                               params={"keyword": "test"}),
                "b": GraphNode(node_id="b", node_name="filter"),
                "c": GraphNode(node_id="c", node_name="market_analysis"),
            },
            edges=[
                GraphEdge(from_node="a", from_output="products",
                          to_node="b", to_input="products"),
                GraphEdge(from_node="b", from_output="filtered_products",
                          to_node="c", to_input="products"),
            ],
            outputs=["c"],
        )
        errors = self.validator.validate(g)
        self.assertEqual(errors, [])

    # ---- Layer 6: Output validity ----

    def test_dangling_output(self):
        """Output referencing a non-existent node should be caught."""
        g = Graph(
            plugin="amazon",
            nodes={
                "ks": GraphNode(node_id="ks", node_name="keyword_search",
                                params={"keyword": "test"}),
            },
            outputs=["nonexistent_node"],
        )
        errors = self.validator.validate(g)
        self.assertTrue(any(e["layer"] == "DANGLING_OUTPUT" for e in errors))

    # ---- validate_or_raise ----

    def test_validate_or_raise_invalid(self):
        """validate_or_raise should raise InvalidGraphError on invalid graph."""
        from core.exceptions import InvalidGraphError
        g = Graph(plugin="amazon", nodes={
            "x": GraphNode(node_id="x", node_name="ghost_node"),
        })
        with self.assertRaises(InvalidGraphError):
            self.validator.validate_or_raise(g)


if __name__ == "__main__":
    unittest.main()
