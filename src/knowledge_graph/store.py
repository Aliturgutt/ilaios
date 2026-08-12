from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .models import Edge, EdgeType, Node, NodeType


class SQLiteGraphStore:
    """Durable, local SQLite persistence for governed knowledge-graph state."""

    def __init__(self, database: str | Path) -> None:
        self._database = str(database)
        self._connection = sqlite3.connect(self._database)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _initialize(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    properties TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_id) REFERENCES nodes(id) ON DELETE CASCADE
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type)"
            )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SQLiteGraphStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def upsert_node(self, node: Node) -> None:
        payload = json.dumps(node.properties, sort_keys=True, separators=(",", ":"))
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO nodes(id, type, properties)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    properties = excluded.properties
                """,
                (node.id, node.type.value, payload),
            )

    def get_node(self, node_id: str) -> Node | None:
        row = self._connection.execute(
            "SELECT id, type, properties FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if row is None:
            return None
        return Node(
            row["id"],
            NodeType(row["type"]),
            self._decode_properties(row["properties"]),
        )

    def delete_node(self, node_id: str) -> bool:
        with self._connection:
            cursor = self._connection.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        return cursor.rowcount > 0

    def upsert_edge(self, edge: Edge) -> None:
        if self.get_node(edge.source) is None or self.get_node(edge.target) is None:
            raise ValueError("edge endpoints must exist before an edge is persisted")
        payload = json.dumps(edge.properties, sort_keys=True, separators=(",", ":"))
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO edges(id, source_id, target_id, type, properties)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_id = excluded.source_id,
                    target_id = excluded.target_id,
                    type = excluded.type,
                    properties = excluded.properties
                """,
                (edge.id, edge.source, edge.target, edge.type.value, payload),
            )

    def get_edge(self, edge_id: str) -> Edge | None:
        row = self._connection.execute(
            """
            SELECT id, source_id, target_id, type, properties
            FROM edges WHERE id = ?
            """,
            (edge_id,),
        ).fetchone()
        return None if row is None else self._edge_from_row(row)

    def query_edges(
        self,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: EdgeType | None = None,
    ) -> list[Edge]:
        clauses: list[str] = []
        values: list[str] = []
        if source_id is not None:
            clauses.append("source_id = ?")
            values.append(source_id)
        if target_id is not None:
            clauses.append("target_id = ?")
            values.append(target_id)
        if edge_type is not None:
            clauses.append("type = ?")
            values.append(edge_type.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            "SELECT id, source_id, target_id, type, properties FROM edges" + where + " ORDER BY id",
            values,
        ).fetchall()
        return [self._edge_from_row(row) for row in rows]

    def neighbors(
        self, node_id: str, *, edge_type: EdgeType | None = None
    ) -> list[Node]:
        edges = self.query_edges(source_id=node_id, edge_type=edge_type)
        nodes: list[Node] = []
        for edge in edges:
            node = self.get_node(edge.target)
            if node is not None:
                nodes.append(node)
        return nodes

    def iter_nodes(self, node_type: NodeType | None = None) -> Iterator[Node]:
        if node_type is None:
            rows = self._connection.execute(
                "SELECT id, type, properties FROM nodes ORDER BY id"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT id, type, properties FROM nodes WHERE type = ? ORDER BY id",
                (node_type.value,),
            ).fetchall()
        for row in rows:
            yield Node(
                row["id"],
                NodeType(row["type"]),
                self._decode_properties(row["properties"]),
            )

    @staticmethod
    def _decode_properties(raw: str) -> dict[str, Any]:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("persisted graph properties must decode to an object")
        return value

    @classmethod
    def _edge_from_row(cls, row: sqlite3.Row) -> Edge:
        return Edge(
            row["id"],
            row["source_id"],
            row["target_id"],
            EdgeType(row["type"]),
            cls._decode_properties(row["properties"]),
        )
