from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from services.software_factory_final_evidence_runner import (
    FinalEvidenceRunnerError,
    run_final_evidence,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY_ROOT / "evidence/software_factory/final_evidence.json"


def _sha(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPOSITORY_ROOT, text=True).strip()


def _is_shallow() -> bool:
    return _sha("rev-parse", "--is-shallow-repository") == "true"


def test_observed_software_factory_final_evidence_reconciles() -> None:
    if _is_shallow():
        pytest.skip("full Git ancestry is enforced by the dedicated final-evidence CI job")
    head = _sha("rev-parse", "HEAD")
    base = _sha("rev-parse", "HEAD^")
    commercial, e2e, completeness, final = run_final_evidence(
        REPOSITORY_ROOT,
        MANIFEST,
        base_sha=base,
        head_sha=head,
    )
    assert commercial.passed is True
    assert e2e.passed is True
    assert completeness.passed is True
    assert final.passed is True
    assert final.final_completion_claimed is True
    assert final.deployment_authorized is False
    assert final.production_mutation_authorized is False


def test_tampered_phase_evidence_digest_fails_closed(tmp_path: Path) -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    document["phases"][0]["evidence_digest"] = "0" * 64
    tampered = tmp_path / "tampered-final-evidence.json"
    tampered.write_text(json.dumps(document), encoding="utf-8")
    if _is_shallow():
        pytest.skip("full Git ancestry is enforced by the dedicated final-evidence CI job")
    head = _sha("rev-parse", "HEAD")
    base = _sha("rev-parse", "HEAD^")
    with pytest.raises(FinalEvidenceRunnerError, match="digest mismatch"):
        run_final_evidence(
            REPOSITORY_ROOT,
            tampered,
            base_sha=base,
            head_sha=head,
        )
