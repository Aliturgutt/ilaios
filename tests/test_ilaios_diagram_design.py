from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ilaios_diagram_design import (
    DiagramEdge,
    DiagramKind,
    DiagramNode,
    DiagramSpec,
    DiagramValidationError,
    Direction,
    EdgeKind,
    render_diagram,
)


def _spec(*, kind: DiagramKind = DiagramKind.ARCHITECTURE) -> DiagramSpec:
    return DiagramSpec(
        title="Governed execution",
        description="Deterministic ILAIOS diagram proof.",
        kind=kind,
        direction=Direction.LEFT_TO_RIGHT,
        nodes=(
            DiagramNode("goal", "Authenticated Goal", kind="input"),
            DiagramNode(
                "control",
                "Control Plane",
                subtitle="policy · budget · approval",
                kind="platform",
                focal=True,
            ),
            DiagramNode("worker", "Governed Worker", kind="worker"),
        ),
        edges=(
            DiagramEdge("goal", "control", "ADMIT"),
            DiagramEdge("control", "worker", "ROUTE", EdgeKind.ACCENT),
        ),
    )


def test_render_is_deterministic_and_emits_evidence() -> None:
    first = render_diagram(_spec())
    second = render_diagram(_spec())

    assert first.svg == second.svg
    assert first.spec_sha256 == second.spec_sha256
    assert first.artifact_sha256 == second.artifact_sha256
    assert len(first.spec_sha256) == 64
    assert len(first.artifact_sha256) == 64
    assert "standalone-svg" in first.checks
    assert "#00C2D1" in first.svg
    assert 'role="img"' in first.svg


def test_user_markup_is_escaped_and_never_executed() -> None:
    spec = DiagramSpec(
        title="Escaping",
        description="Raw markup is data.",
        kind=DiagramKind.ARCHITECTURE,
        nodes=(
            DiagramNode("source", "<script>alert(1)</script>", kind="input"),
            DiagramNode("target", "Safe", kind="output"),
        ),
        edges=(DiagramEdge("source", "target", "<b>NO</b>"),),
    )

    artifact = render_diagram(spec)

    assert "<script>" not in artifact.svg
    assert "<b>NO</b>" not in artifact.svg
    assert "&lt;script&gt;alert(1)" in artifact.svg
    assert "&lt;b&gt;NO&lt;/b&gt;" in artifact.svg


def test_unknown_edge_reference_fails_closed() -> None:
    spec = DiagramSpec(
        title="Invalid edge",
        description="Unknown references must fail.",
        kind=DiagramKind.DATA_FLOW,
        nodes=(DiagramNode("known", "Known"),),
        edges=(DiagramEdge("known", "missing"),),
    )

    with pytest.raises(DiagramValidationError, match="unknown node"):
        render_diagram(spec)


def test_complexity_budget_rejects_dense_architecture() -> None:
    nodes = tuple(
        DiagramNode(f"node-{index}", f"Node {index}")
        for index in range(13)
    )
    spec = DiagramSpec(
        title="Too dense",
        description="Must be split.",
        kind=DiagramKind.ARCHITECTURE,
        nodes=nodes,
        edges=(),
    )

    with pytest.raises(DiagramValidationError, match="at most 12 nodes"):
        render_diagram(spec)


def test_sequence_uses_ordered_messages_and_accessible_metadata() -> None:
    spec = DiagramSpec(
        title="Sequence",
        description="Ordered message flow.",
        kind=DiagramKind.SEQUENCE,
        nodes=(
            DiagramNode("control", "Control Plane", subtitle="authority"),
            DiagramNode("worker", "Worker", subtitle="execution"),
            DiagramNode("evidence", "Evidence", subtitle="append-only"),
        ),
        edges=(
            DiagramEdge("control", "worker", "AUTHORIZED", EdgeKind.ACCENT),
            DiagramEdge("worker", "evidence", "WRITE", EdgeKind.ASYNC),
        ),
    )

    artifact = render_diagram(spec)

    assert "AUTHORIZED" in artifact.svg
    assert "WRITE" in artifact.svg
    assert 'stroke-dasharray="4 5"' in artifact.svg
    assert "<title " in artifact.svg
    assert "<desc " in artifact.svg


def test_manifest_is_ilaios_native_and_provider_independent() -> None:
    manifest_path = Path("skills/ilaios-diagram-design/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["skill_id"] == "ilaios.skill.diagram-design"
    assert manifest["maturity"] == "IMPLEMENTED"
    assert manifest["runtime"]["external_runtime_dependencies"] == []
    assert manifest["permissions"]["network"] is False
    assert manifest["permissions"]["shell"] is False
    assert "production" not in manifest["maturity"].casefold()
