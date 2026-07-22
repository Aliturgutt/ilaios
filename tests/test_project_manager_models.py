"""Tests for src.project_manager.models."""

from src.project_manager.models import Project, ProjectState, Workspace


def test_project_defaults_to_active_state() -> None:
    project = Project(project_id="p-1", name="Demo", path="/tmp/demo")
    assert project.state == ProjectState.ACTIVE


def test_project_metadata_starts_empty() -> None:
    project = Project(project_id="p-1", name="Demo", path="/tmp/demo")
    assert project.metadata == {}


def test_workspace_can_add_project() -> None:
    workspace = Workspace()
    project = Project(project_id="p-1", name="Demo", path="/tmp/demo")
    workspace.add_project(project)
    assert workspace.get_project("p-1") is project


def test_workspace_get_project_by_id() -> None:
    workspace = Workspace()
    project = Project(project_id="p-1", name="Demo", path="/tmp/demo")
    workspace.add_project(project)
    assert workspace.get_project("missing") is None
    assert workspace.get_project("p-1") is project


def test_workspace_list_projects_filters_by_state() -> None:
    workspace = Workspace()
    active = Project(project_id="p-1", name="Active", path="/tmp/a")
    archived = Project(
        project_id="p-2",
        name="Archived",
        path="/tmp/b",
        state=ProjectState.ARCHIVED,
    )
    workspace.add_project(active)
    workspace.add_project(archived)

    assert workspace.list_projects() == [active, archived]
    assert workspace.list_projects(state=ProjectState.ACTIVE) == [active]
    assert workspace.list_projects(state=ProjectState.ARCHIVED) == [archived]


def test_project_instances_do_not_share_metadata_dict() -> None:
    project_a = Project(project_id="p-1", name="A", path="/tmp/a")
    project_b = Project(project_id="p-2", name="B", path="/tmp/b")

    project_a.metadata["key"] = "value"

    assert project_b.metadata == {}
    assert project_a.metadata is not project_b.metadata
