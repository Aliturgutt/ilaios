from pathlib import Path

from src.project_manager.models import Project, ProjectState
from src.project_manager.store import SQLiteProjectStore


def test_project_lifecycle_persists_across_restart(tmp_path: Path) -> None:
    database = tmp_path / "projects.db"
    project = Project("ilaios", "ILAIOS", "/workspace/ilaios")
    project.metadata["owner"] = "canonical"

    with SQLiteProjectStore(database) as store:
        store.save(project)

    with SQLiteProjectStore(database) as reopened:
        loaded = reopened.load("ilaios")
        assert loaded is not None
        assert loaded.name == "ILAIOS"
        assert loaded.path == "/workspace/ilaios"
        assert loaded.state is ProjectState.ACTIVE
        assert loaded.metadata == {"owner": "canonical"}

        created_at = loaded.created_at
        loaded.name = "ILAIOS Enterprise AI OS"
        loaded.metadata["phase"] = "verified"
        reopened.save(loaded)

        updated = reopened.load("ilaios")
        assert updated is not None
        assert updated.created_at == created_at
        assert updated.name == "ILAIOS Enterprise AI OS"
        assert updated.metadata["phase"] == "verified"

        archived = reopened.archive("ilaios")
        assert archived.state is ProjectState.ARCHIVED
        assert [item.id for item in reopened.list(ProjectState.ARCHIVED)] == ["ilaios"]

        workspace = reopened.load_workspace()
        assert workspace.get_project("ilaios") is not None

        assert reopened.delete("ilaios") is True
        assert reopened.load("ilaios") is None
        assert reopened.delete("ilaios") is False
