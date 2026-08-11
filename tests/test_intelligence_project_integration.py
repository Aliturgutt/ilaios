"""Fresh integration revalidation for ILAIOS intelligence/project foundations."""

from pathlib import Path

from src.code_intelligence import Language, SourceFileAnalyzer
from src.knowledge_graph.models import Edge, EdgeType, Node, NodeType
from src.project_manager.models import Project, ProjectState, Workspace


def test_source_analysis_can_feed_project_and_knowledge_context(tmp_path: Path) -> None:
    repository = tmp_path / "demo"
    source = repository / "src" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_text("def run() -> int:\n    return 1\n", encoding="utf-8")

    analyzed = SourceFileAnalyzer(repository).analyze("src/example.py")
    assert analyzed.language is Language.PYTHON
    assert analyzed.path == "src/example.py"
    assert analyzed.line_count == 2

    project = Project(project_id="project-demo", name="Demo", path=str(repository))
    workspace = Workspace()
    workspace.add_project(project)
    assert workspace.get_project(project.id) is project
    assert project.state is ProjectState.ACTIVE

    project_node = Node(
        node_id=f"project:{project.id}",
        node_type=NodeType.PROJECT,
        properties={"name": project.name, "path": project.path},
    )
    file_node = Node(
        node_id=f"file:{analyzed.path}",
        node_type=NodeType.FILE,
        properties={
            "path": analyzed.path,
            "language": analyzed.language.value,
            "line_count": analyzed.line_count,
        },
    )
    contains = Edge(
        edge_id=f"contains:{project.id}:{analyzed.path}",
        source_id=project_node.id,
        target_id=file_node.id,
        edge_type=EdgeType.CONTAINS,
    )

    assert contains.source == project_node.id
    assert contains.target == file_node.id
    assert file_node.properties["path"] == analyzed.path
    assert file_node.properties["line_count"] == 2
