"""Tests for src.knowledge_graph.models."""

from src.knowledge_graph.models import Edge, EdgeType, Node, NodeType


def test_node_can_be_constructed() -> None:
    node = Node(node_id="n-1", node_type=NodeType.FILE, properties={"path": "a.py"})
    assert node.id == "n-1"
    assert node.type == NodeType.FILE
    assert node.properties == {"path": "a.py"}


def test_edge_can_be_constructed() -> None:
    edge = Edge(
        edge_id="e-1",
        source_id="n-1",
        target_id="n-2",
        edge_type=EdgeType.CONTAINS,
    )
    assert edge.id == "e-1"
    assert edge.source == "n-1"
    assert edge.target == "n-2"
    assert edge.type == EdgeType.CONTAINS


def test_edge_properties_none_yields_empty_dict() -> None:
    edge = Edge(
        edge_id="e-1",
        source_id="n-1",
        target_id="n-2",
        edge_type=EdgeType.CONTAINS,
        properties=None,
    )
    assert edge.properties == {}


def test_edge_instances_do_not_share_default_properties_dict() -> None:
    edge_a = Edge(
        edge_id="e-a",
        source_id="n-1",
        target_id="n-2",
        edge_type=EdgeType.CONTAINS,
    )
    edge_b = Edge(
        edge_id="e-b",
        source_id="n-3",
        target_id="n-4",
        edge_type=EdgeType.CONTAINS,
    )

    edge_a.properties["key"] = "value"

    assert edge_b.properties == {}
    assert edge_a.properties is not edge_b.properties
