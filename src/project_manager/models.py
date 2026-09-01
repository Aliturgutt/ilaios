from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ProjectState(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    TEMPLATE = "template"


class Project:
    """Represents a managed project."""

    def __init__(self,
                 project_id: str,
                 name: str,
                 path: str,
                 state: ProjectState = ProjectState.ACTIVE) -> None:
        self.id = project_id
        self.name = name
        self.path = path
        self.state = state
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metadata: dict[str, Any] = {}


class Workspace:
    """Manages multiple projects."""

    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    def add_project(self, project: Project) -> None:
        """Add a project to the workspace."""
        self.projects[project.id] = project

    def get_project(self, project_id: str) -> Project | None:
        """Retrieve a project by ID."""
        return self.projects.get(project_id)

    def list_projects(self, state: ProjectState | None = None) -> list[Project]:
        """List projects optionally filtered by state."""
        if state is None:
            return list(self.projects.values())
        return [p for p in self.projects.values() if p.state == state]
