from pathlib import Path

import pytest

from src.knowledge_graph.models import Edge, EdgeType, Node, NodeType
from src.knowledge_graph.store import SQLiteGraphStore


def test_graph_persists_and_queries_across_restart(tmp_path: Path) -> None:
    database = tmp_path / "knowledge.db"

    with SQLiteGraphStore(database) as store:
        store.upsert_node(Node("project:ilaios", NodeType.PROJECT, {"name": "ILAIOS"}))
        store.upsert_node(Node("repo:canonical", NodeType.REPOSITORY, {"branch": "master"}))
        store.upsert_edge(
            Edge(
                "edge:project-repo",
                "project:ilaios",
                "repo:canonical",
                EdgeType.CONTAINS,
                {"governed": True},
            )
        )

    with SQLiteGraphStore(database) as reopened:
        project = reopened.get_node("project:ilaios")
        assert project is not None
        assert project.type is NodeType.PROJECT
        assert project.properties == {"name": "ILAIOS"}

        edges = reopened.query_edges(
            source_id="project:ilaios", edge_type=EdgeType.CONTAINS
        )
        assert [edge.target for edge in edges] == ["repo:canonical"]
        assert edges[0].properties == {"governed": True}

        neighbors = reopened.neighbors("project:ilaios", edge_type=EdgeType.CONTAINS)
        assert [node.id for node in neighbors] == ["repo:canonical"]


def test_graph_rejects_edges_with_missing_endpoints(tmp_path: Path) -> None:
    with SQLiteGraphStore(tmp_path / "knowledge.db") as store:
        store.upsert_node(Node("source", NodeType.FACT, {}))
        with pytest.raises(ValueError, match="endpoints must exist"):
            store.upsert_edge(
                Edge("broken", "source", "missing", EdgeType.RELATED_TO)
            )


def test_deleting_node_cascades_edges(tmp_path: Path) -> None:
    with SQLiteGraphStore(tmp_path / "knowledge.db") as store:
        store.upsert_node(Node("source", NodeType.FACT, {}))
        store.upsert_node(Node("target", NodeType.EVIDENCE, {}))
        store.upsert_edge(Edge("relationship", "source", "target", EdgeType.VERIFIES))

        assert store.delete_node("target") is True
        assert store.get_edge("relationship") is None
