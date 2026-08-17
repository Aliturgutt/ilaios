"""End-to-end system-design to diagram-design contract tests."""

from __future__ import annotations

from src.ilaios_diagram_design import validate_svg
from src.system_design import (
    CapacityInput,
    SystemDesignRequest,
    architecture_to_diagram_spec,
    render_architecture_diagram,
    run_system_design,
)


def _architecture() -> dict[str, object]:
    result = run_system_design(
        SystemDesignRequest(
            system_id="diagram-e2e",
            capacity=CapacityInput(
                requests_per_second=5_000,
                peak_factor=2,
                read_ratio=0.8,
                write_ratio=0.2,
                availability_slo=0.9999,
            ),
            availability_slo=0.9999,
            asynchronous_workload_fraction=0.2,
        )
    )
    return result.architecture


def test_system_design_schema_maps_to_existing_diagram_skill() -> None:
    spec = architecture_to_diagram_spec(_architecture())
    assert spec.title == "diagram-e2e — System Architecture"
    assert {node.node_id for node in spec.nodes} >= {
        "application",
        "primary-database",
        "work-queue",
    }


def test_system_design_architecture_renders_with_evidence_hashes() -> None:
    artifact = render_architecture_diagram(_architecture(), dark_mode=True)
    checks = validate_svg(artifact.svg)
    assert artifact.spec_sha256
    assert artifact.artifact_sha256
    assert "standalone-svg" in checks
    assert "ilaios-flat-vector-policy" in artifact.checks
