from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Project, ProjectState, Workspace


class SQLiteProjectStore:
    """Durable persistence for ILAIOS project/workspace lifecycle state."""

    def __init__(self, database: str | Path) -> None:
        self._connection = sqlite3.connect(str(database))
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_state ON projects(state)"
            )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SQLiteProjectStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def save(self, project: Project) -> None:
        project.updated_at = datetime.now(project.updated_at.tzinfo)
        metadata = json.dumps(project.metadata, sort_keys=True, separators=(",", ":"))
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO projects(id, name, path, state, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    path = excluded.path,
                    state = excluded.state,
                    updated_at = excluded.updated_at,
                    metadata = excluded.metadata
                """,
                (
                    project.id,
                    project.name,
                    project.path,
                    project.state.value,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                    metadata,
                ),
            )

    def load(self, project_id: str) -> Project | None:
        row = self._connection.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return None if row is None else self._project_from_row(row)

    def list(self, state: ProjectState | None = None) -> list[Project]:
        if state is None:
            rows = self._connection.execute(
                "SELECT * FROM projects ORDER BY id"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM projects WHERE state = ? ORDER BY id", (state.value,)
            ).fetchall()
        return [self._project_from_row(row) for row in rows]

    def archive(self, project_id: str) -> Project:
        project = self._require(project_id)
        project.state = ProjectState.ARCHIVED
        self.save(project)
        return project

    def delete(self, project_id: str) -> bool:
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM projects WHERE id = ?", (project_id,)
            )
        return cursor.rowcount > 0

    def load_workspace(self) -> Workspace:
        workspace = Workspace()
        for project in self.list():
            workspace.add_project(project)
        return workspace

    def _require(self, project_id: str) -> Project:
        project = self.load(project_id)
        if project is None:
            raise KeyError(project_id)
        return project

    @staticmethod
    def _decode_metadata(raw: str) -> dict[str, Any]:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("persisted project metadata must decode to an object")
        return value

    @classmethod
    def _project_from_row(cls, row: sqlite3.Row) -> Project:
        project = Project(
            project_id=row["id"],
            name=row["name"],
            path=row["path"],
            state=ProjectState(row["state"]),
        )
        project.created_at = datetime.fromisoformat(row["created_at"])
        project.updated_at = datetime.fromisoformat(row["updated_at"])
        project.metadata = cls._decode_metadata(row["metadata"])
        return project
