from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path

import pytest

from services.web_reference_semantics import (
    WebReferenceSemanticBrief,
    WebSemanticObservation,
)
from services.web_revision_planner import (
    GovernedWebRevisionPlanner,
    WebRevisionPlanningEnvelope,
    WebRevisionPlanningError,
)
from services.web_source_ingestion import WebSourceArchiveIngestor, WebSourceSnapshot
from services.web_source_revision import WebSourceRevisionRequest


def _archive() -> bytes:
    files = {
        "package.json": json.dumps(
            {
                "dependencies": {"next": "16.2.11", "react": "19.2.0"},
            }
        ).encode(),
        "app/page.tsx": b"export default function Page(){return <main>Old</main>}",
        "components/Hero.tsx": b"export function Hero(){return <section>Hero</section>}",
        "public/logo.svg": b"<svg></svg>",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path, body in files.items():
            bundle.writestr(path, body)
    return buffer.getvalue()


class _Transport:
    planner_id = "governed-web-planner:test"

    def __init__(self) -> None:
        self.envelopes: list[WebRevisionPlanningEnvelope] = []

    def propose_revision(
        self, envelope: WebRevisionPlanningEnvelope
    ) -> Mapping[str, object]:
        self.envelopes.append(envelope)
        return {
            "operations": [
                {
                    "operation": "replace",
                    "relative_path": "app/page.tsx",
                    "content": "export default function Page(){return <main>New dashboard</main>}",
                },
                {
                    "operation": "create",
                    "relative_path": "components/Stats.tsx",
                    "content": "export function Stats(){return <section>Stats</section>}",
                },
            ]
        }


class _UnsafeTransport:
    planner_id = "governed-web-planner:unsafe"

    def propose_revision(
        self, envelope: WebRevisionPlanningEnvelope
    ) -> Mapping[str, object]:
        del envelope
        return {
            "operations": [
                {
                    "operation": "create",
                    "relative_path": "components/Unsafe.tsx",
                    "content": "export const x = eval('1')",
                }
            ]
        }


class _DependencyMutationTransport:
    planner_id = "governed-web-planner:dependency"

    def propose_revision(
        self, envelope: WebRevisionPlanningEnvelope
    ) -> Mapping[str, object]:
        del envelope
        return {
            "operations": [
                {
                    "operation": "replace",
                    "relative_path": "package.json",
                    "content": "{}",
                }
            ]
        }


def _snapshot(tmp_path: Path) -> WebSourceSnapshot:
    return WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(_archive())


def _semantic() -> WebReferenceSemanticBrief:
    observation = WebSemanticObservation(
        category="layout",
        text="Persistent left navigation with a dense primary workspace.",
    )
    return WebReferenceSemanticBrief(
        schema_version="ilaios.web.reference-semantics.v1",
        observations=(observation,),
        reference_sha256s=("1" * 64,),
        analyzer_id="governed-web-visual:test",
        analysis_sha256="a" * 64,
    )


def test_planner_binds_exact_source_semantics_and_preimages(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    transport = _Transport()
    planner = GovernedWebRevisionPlanner(transport)
    request = WebSourceRevisionRequest(
        "request-plan-1",
        "Upgrade this dashboard to match the supplied visual hierarchy.",
        semantic_analysis_sha256="a" * 64,
    )

    receipt = planner.plan(snapshot, request, semantic_brief=_semantic())

    assert receipt.planner_id == transport.planner_id
    assert receipt.source_tree_sha256 == snapshot.tree_sha256
    assert receipt.semantic_analysis_sha256 == "a" * 64
    assert len(receipt.proposal_sha256) == 64
    assert receipt.plan.plan_id.startswith("web-plan-")
    assert receipt.plan.source_tree_sha256 == snapshot.tree_sha256
    assert len(receipt.plan.operations) == 2
    replace = receipt.plan.operations[0]
    source_record = next(
        item for item in snapshot.files if item.relative_path == "app/page.tsx"
    )
    assert replace.expected_sha256 == source_record.sha256
    assert transport.envelopes[0].semantic_observations == (
        {
            "category": "layout",
            "text": "Persistent left navigation with a dense primary workspace.",
        },
    )
    assert "untrusted" in transport.envelopes[0].instructions
    assert {doc.relative_path for doc in transport.envelopes[0].source_documents} == {
        "app/page.tsx",
        "components/Hero.tsx",
    }
    assert all(
        doc.relative_path != "public/logo.svg"
        for doc in transport.envelopes[0].source_documents
    )


def test_planner_output_is_deterministic_for_same_proposal(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    request = WebSourceRevisionRequest("request-plan-2", "Refine the existing UI.")

    first = GovernedWebRevisionPlanner(_Transport()).plan(snapshot, request)
    second = GovernedWebRevisionPlanner(_Transport()).plan(snapshot, request)

    assert first.proposal_sha256 == second.proposal_sha256
    assert first.plan == second.plan


def test_planner_requires_semantic_brief_when_request_binds_digest(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    request = WebSourceRevisionRequest(
        "request-plan-3",
        "Use the reference layout.",
        semantic_analysis_sha256="a" * 64,
    )

    with pytest.raises(WebRevisionPlanningError, match="requires the referenced semantic"):
        GovernedWebRevisionPlanner(_Transport()).plan(snapshot, request)


def test_planner_rejects_semantic_digest_mismatch(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    request = WebSourceRevisionRequest(
        "request-plan-4",
        "Use the reference layout.",
        semantic_analysis_sha256="b" * 64,
    )

    with pytest.raises(WebRevisionPlanningError, match="does not match"):
        GovernedWebRevisionPlanner(_Transport()).plan(
            snapshot,
            request,
            semantic_brief=_semantic(),
        )


def test_planner_rejects_unsafe_provider_source(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)

    with pytest.raises(WebRevisionPlanningError, match="forbidden source pattern: eval"):
        GovernedWebRevisionPlanner(_UnsafeTransport()).plan(
            snapshot,
            WebSourceRevisionRequest("request-plan-5", "Add a safe component."),
        )


def test_planner_rejects_dependency_mutation(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)

    with pytest.raises(
        WebRevisionPlanningError,
        match="replace proposal target does not exist|bounded source roots",
    ):
        GovernedWebRevisionPlanner(_DependencyMutationTransport()).plan(
            snapshot,
            WebSourceRevisionRequest("request-plan-6", "Update the UI only."),
        )
