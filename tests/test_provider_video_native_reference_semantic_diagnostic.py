from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from apps.desktop.e2e.provider_video_native_reference_semantic_diagnostic_e2e import (
    _select_failure_review,
    _semantic_review_stage,
    semantic_review_evidence,
)
from src.video_automation.perceptual_review import (
    PerceptualReviewSubmission,
    PerceptualReviewerKind,
)
from src.video_automation.video_skills import QaDomain


def _review(
    *,
    review_id: str,
    score: float,
    threshold: float = 0.78,
    repair_target: str | None = None,
) -> PerceptualReviewSubmission:
    return PerceptualReviewSubmission(
        review_id=review_id,
        domain=QaDomain.VISUAL,
        artifact_sha256="a" * 64,
        reviewer_id="openrouter-semantic-review:test-model",
        producer_id="ilaios-provider-video-factory",
        reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
        criteria_id="ilaios.video.semantic-prompt-alignment",
        criteria_version="1.0.0",
        criteria_sha256="b" * 64,
        score=score,
        threshold=threshold,
        evidence_references=("frame-sha256:" + "c" * 64,),
        provenance_reference="openrouter-review:model=test-model:artifact=" + "a" * 64,
        repair_target=repair_target,
    )


def test_semantic_review_evidence_preserves_fail_closed_rejection_details() -> None:
    review = _review(
        review_id="native-reference-final",
        score=0.62,
        repair_target="preserve-product-identity",
    )

    evidence = semantic_review_evidence(review)

    assert evidence == {
        "review_id": "native-reference-final",
        "reviewer_id": "openrouter-semantic-review:test-model",
        "score": 0.62,
        "threshold": 0.78,
        "passed": False,
        "repair_target": "preserve-product-identity",
        "criteria_id": "ilaios.video.semantic-prompt-alignment",
        "criteria_version": "1.0.0",
        "criteria_sha256": "b" * 64,
        "provenance_reference": "openrouter-review:model=test-model:artifact=" + "a" * 64,
    }


def test_failure_review_selection_captures_generated_shot_rejection() -> None:
    accepted = _review(review_id="request-clip-001", score=0.91)
    rejected = _review(
        review_id="request-clip-002",
        score=0.54,
        repair_target="match-admitted-product-reference",
    )

    selected = _select_failure_review([accepted, rejected])

    assert selected is rejected
    assert _semantic_review_stage(selected) == "generated-shot"
    assert semantic_review_evidence(selected)["repair_target"] == (
        "match-admitted-product-reference"
    )


def test_failure_review_selection_preserves_final_stage() -> None:
    final = _review(
        review_id="request-final",
        score=0.66,
        repair_target="preserve-product-identity",
    )

    selected = _select_failure_review([final])

    assert selected is final
    assert _semantic_review_stage(selected) == "final"


def test_semantic_diagnostic_direct_script_bootstraps_repo_imports(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = (
        repo_root
        / "apps"
        / "desktop"
        / "e2e"
        / "provider_video_native_reference_semantic_diagnostic_e2e.py"
    )
    env = os.environ.copy()
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", None)
    env.pop("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", None)

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "OPENROUTER_API_KEY is required for native-reference E2E" in output
    assert "ModuleNotFoundError" not in output
