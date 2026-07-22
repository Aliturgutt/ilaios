from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


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
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.metadata: Dict[str, Any] = {}


class Workspace:
    """Manages multiple projects."""

    def __init__(self) -> None:
        self.projects: Dict[str, Project] = {}

    def add_project(self, project: Project) -> None:
        """Add a project to the workspace."""
        self.projects[project.id] = project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve a project by ID."""
        return self.projects.get(project_id)

    def list_projects(self, state: Optional[ProjectState] = None) -> List[Project]:
        """List projects optionally filtered by state."""
        if state is None:
            return list(self.projects.values())
        return [p for p in self.projects.values() if p.state == state]
