from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.evidence import EvidenceStore
from services.runtime import BlastRadiusBudget, ExecutionGrant
from services.web_source_ingestion import WebSourceArchiveIngestor, WebSourceSnapshot
from services.web_source_revision import (
    GovernedWebSourceRevisionEngine,
    WebSourceRevisionError,
    WebSourceRevisionOperation,
    WebSourceRevisionPlan,
    WebSourceRevisionRequest,
)


class _GrantBoundary:
    def __init__(self, *, allow: bool = True) -> None:
        self.allow = allow
        self.calls: list[tuple[str, str, str]] = []

    def authorize(
        self,
        grant: ExecutionGrant,
        *,
        subject_id: str,
        action: str,
        resource: str,
        now: datetime,
    ) -> None:
        assert now.tzinfo is not None
        self.calls.append((subject_id, action, resource))
        if not self.allow:
            raise PermissionError("denied by canonical grant boundary")
        assert grant.subject_id == subject_id
        assert action in grant.actions
        assert resource in grant.resources
        assert now < grant.expires_at


def _zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, body in files.items():
            bundle.writestr(relative, body)
    return buffer.getvalue()


def _source_files() -> dict[str, bytes]:
    return {
        "package.json": json.dumps(
            {
                "name": "existing-site",
                "dependencies": {"next": "16.2.11", "react": "19.2.0"},
            },
            sort_keys=True,
        ).encode(),
        "app/page.tsx": b"export default function Page(){return <main>Old</main>}",
        "app/globals.css": b"body { margin: 0; }",
        "components/Hero.tsx": b"export function Hero(){return <section>Hero</section>}",
    }


def _snapshot(tmp_path: Path) -> WebSourceSnapshot:
    return WebSourceArchiveIngestor(tmp_path / "artifacts").ingest_zip(
        _zip(_source_files())
    )


def _grant(snapshot_id: str) -> ExecutionGrant:
    return ExecutionGrant(
        "grant-web-revision-1",
        "web-revision-worker",
        frozenset({"web.source.revise"}),
        frozenset({snapshot_id}),
        datetime(2026, 8, 20, tzinfo=timezone.utc),
        BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )


def test_revision_is_copy_on_write_digest_bound_and_appends_canonical_evidence(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path)
    original = Path(snapshot.root_path) / "app/page.tsx"
    original_bytes = original.read_bytes()
    semantic_digest = "a" * 64
    replacement = b"export default function Page(){return <main>New dashboard</main>}"
    operation = WebSourceRevisionOperation(
        "replace",
        "app/page.tsx",
        expected_sha256=hashlib.sha256(original_bytes).hexdigest(),
        content=replacement,
    )
    plan = WebSourceRevisionPlan(
        "plan-web-revision-1",
        snapshot.tree_sha256,
        (operation,),
        semantic_analysis_sha256=semantic_digest,
    )
    request = WebSourceRevisionRequest(
        "request-web-revision-1",
        "Upgrade the existing dashboard while preserving its source lineage.",
        semantic_analysis_sha256=semantic_digest,
    )
    grants = _GrantBoundary()
    evidence = EvidenceStore(tmp_path / "evidence")
    engine = GovernedWebSourceRevisionEngine(tmp_path / "revisions", grants, evidence)

    receipt = engine.apply(
        snapshot,
        request,
        plan,
        grant=_grant(snapshot.snapshot_id),
        now=datetime(2026, 8, 19, 1, 30, tzinfo=timezone.utc),
    )

    assert original.read_bytes() == original_bytes
    revised = Path(receipt.revised_root_path)
    assert (revised / "app/page.tsx").read_bytes() == replacement
    assert receipt.source_tree_sha256 == snapshot.tree_sha256
    assert receipt.revised_tree_sha256 != snapshot.tree_sha256
    assert receipt.changed_paths == ("app/page.tsx",)
    assert receipt.semantic_analysis_sha256 == semantic_digest
    assert grants.calls == [
        ("web-revision-worker", "web.source.revise", snapshot.snapshot_id)
    ]
    records = evidence.verify()
    assert len(records) == 1
    assert records[0].execution_id == request.request_id
    assert records[0].action == "web.source.revision"
    assert records[0].artifact_digest == receipt.evidence_artifact_sha256
    assert records[0].record_hash == receipt.evidence_record_hash


def test_revision_can_create_bounded_source_file(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    operation = WebSourceRevisionOperation(
        "create",
        "components/Stats.tsx",
        content=b"export function Stats(){return <section>Stats</section>}",
    )
    plan = WebSourceRevisionPlan(
        "plan-create-component",
        snapshot.tree_sha256,
        (operation,),
    )
    receipt = GovernedWebSourceRevisionEngine(
        tmp_path / "revisions",
        _GrantBoundary(),
        EvidenceStore(tmp_path / "evidence"),
    ).apply(
        snapshot,
        WebSourceRevisionRequest("request-create-component", "Add a stats component."),
        plan,
        grant=_grant(snapshot.snapshot_id),
        now=datetime(2026, 8, 19, 1, 31, tzinfo=timezone.utc),
    )

    assert (Path(receipt.revised_root_path) / "components/Stats.tsx").is_file()


def test_revision_rejects_stale_preimage_before_authorization(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    operation = WebSourceRevisionOperation(
        "replace",
        "app/page.tsx",
        expected_sha256="b" * 64,
        content=b"export default function Page(){return <main>Changed</main>}",
    )
    grants = _GrantBoundary()
    engine = GovernedWebSourceRevisionEngine(
        tmp_path / "revisions", grants, EvidenceStore(tmp_path / "evidence")
    )

    with pytest.raises(WebSourceRevisionError, match="preimage digest mismatch"):
        engine.apply(
            snapshot,
            WebSourceRevisionRequest("request-stale-plan", "Apply an exact revision."),
            WebSourceRevisionPlan("plan-stale", snapshot.tree_sha256, (operation,)),
            grant=_grant(snapshot.snapshot_id),
            now=datetime(2026, 8, 19, 1, 32, tzinfo=timezone.utc),
        )
    assert grants.calls == []


def test_revision_rejects_source_snapshot_drift_before_authorization(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    source = Path(snapshot.root_path) / "app/page.tsx"
    source.write_text("tampered", encoding="utf-8")
    operation = WebSourceRevisionOperation(
        "replace",
        "app/globals.css",
        expected_sha256=hashlib.sha256(_source_files()["app/globals.css"]).hexdigest(),
        content=b"body { margin: 1px; }",
    )
    grants = _GrantBoundary()

    with pytest.raises(WebSourceRevisionError, match="integrity mismatch"):
        GovernedWebSourceRevisionEngine(
            tmp_path / "revisions", grants, EvidenceStore(tmp_path / "evidence")
        ).apply(
            snapshot,
            WebSourceRevisionRequest("request-drift", "Revise the existing source."),
            WebSourceRevisionPlan("plan-drift", snapshot.tree_sha256, (operation,)),
            grant=_grant(snapshot.snapshot_id),
            now=datetime(2026, 8, 19, 1, 33, tzinfo=timezone.utc),
        )
    assert grants.calls == []


def test_revision_rejects_semantic_evidence_mismatch(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    body = _source_files()["app/globals.css"]
    operation = WebSourceRevisionOperation(
        "replace",
        "app/globals.css",
        expected_sha256=hashlib.sha256(body).hexdigest(),
        content=b"body { margin: 2px; }",
    )
    plan = WebSourceRevisionPlan(
        "plan-semantic-mismatch",
        snapshot.tree_sha256,
        (operation,),
        semantic_analysis_sha256="c" * 64,
    )

    with pytest.raises(WebSourceRevisionError, match="semantic evidence"):
        GovernedWebSourceRevisionEngine(
            tmp_path / "revisions", _GrantBoundary(), EvidenceStore(tmp_path / "evidence")
        ).apply(
            snapshot,
            WebSourceRevisionRequest(
                "request-semantic-mismatch",
                "Use the supplied reference design evidence.",
                semantic_analysis_sha256="d" * 64,
            ),
            plan,
            grant=_grant(snapshot.snapshot_id),
            now=datetime(2026, 8, 19, 1, 34, tzinfo=timezone.utc),
        )


def test_revision_rejects_source_paths_outside_bounded_roots() -> None:
    with pytest.raises(WebSourceRevisionError, match="bounded source roots"):
        WebSourceRevisionOperation(
            "replace",
            "package.json",
            expected_sha256="a" * 64,
            content=b"{}",
        )


def test_revision_rejects_path_traversal() -> None:
    with pytest.raises(WebSourceRevisionError, match="traversal"):
        WebSourceRevisionOperation(
            "create",
            "app/../secrets.ts",
            content=b"export const value = 1",
        )


def test_revision_rejects_dangerous_source_patterns() -> None:
    with pytest.raises(WebSourceRevisionError, match="forbidden source pattern: eval"):
        WebSourceRevisionOperation(
            "create",
            "components/Unsafe.tsx",
            content=b"export const x = eval('1')",
        )


def test_revision_fails_closed_when_canonical_grant_boundary_denies(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    original = _source_files()["app/globals.css"]
    operation = WebSourceRevisionOperation(
        "replace",
        "app/globals.css",
        expected_sha256=hashlib.sha256(original).hexdigest(),
        content=b"body { margin: 3px; }",
    )
    evidence = EvidenceStore(tmp_path / "evidence")

    with pytest.raises(PermissionError, match="denied by canonical grant boundary"):
        GovernedWebSourceRevisionEngine(
            tmp_path / "revisions", _GrantBoundary(allow=False), evidence
        ).apply(
            snapshot,
            WebSourceRevisionRequest("request-denied", "Revise only if admitted."),
            WebSourceRevisionPlan("plan-denied", snapshot.tree_sha256, (operation,)),
            grant=_grant(snapshot.snapshot_id),
            now=datetime(2026, 8, 19, 1, 35, tzinfo=timezone.utc),
        )

    assert evidence.verify() == ()
