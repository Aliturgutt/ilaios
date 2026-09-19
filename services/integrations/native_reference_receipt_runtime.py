"""Evidence-preserving native-reference Desktop Video runtime.

The canonical provider runtime deliberately knows nothing about native-reference
specific QA fields. This additive adapter captures only already-verified native
provider/consistency/logo-lock evidence produced by
``NativeReferenceVerifiedManagedDesktopVideoRuntime`` and carries it into the
canonical ``qa``/result document returned to ProductRuntime. It does not change
provider routing, generation, thresholds, cost policy, or acceptance decisions.
"""

from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

from src.video_automation.logo_asset_lock import LogoAssetLockResult
from src.video_automation.reference_consistency_review import (
    OpenRouterReferenceConsistencyReviewer,
    ReferenceConsistencyReview,
)

from .native_reference_verified_runtime import (
    NativeReferenceVerifiedManagedDesktopVideoRuntime,
)

_NATIVE_QA_PREFIXES = ("reference_consistency_", "logo_asset_lock_")
_NATIVE_PROVIDER_KEYS = frozenset(
    {
        "provider_native_reference_url_used",
        "native_reference_mode",
        "native_reference_count",
        "native_reference_dispatch_count",
        "native_reference_sha256s",
        "native_reference_relay_released",
    }
)
_NATIVE_CONSISTENCY_MODEL_ID = "google/gemma-4-26b-a4b-it:free"


def native_receipt_evidence(outcome: dict[str, object]) -> dict[str, object]:
    """Return verified native-reference fields that may enter final receipts."""

    if outcome.get("reference_consistency_passed") is not True:
        raise RuntimeError("native reference receipt lacks consistency PASS evidence")
    missing = sorted(key for key in _NATIVE_PROVIDER_KEYS if key not in outcome)
    if missing:
        raise RuntimeError("native reference receipt lacks provider relay evidence")
    if outcome.get("native_reference_relay_released") is not True:
        raise RuntimeError("native reference receipt lacks relay release evidence")
    evidence = {
        key: value
        for key, value in outcome.items()
        if key.startswith(_NATIVE_QA_PREFIXES) or key in _NATIVE_PROVIDER_KEYS
    }
    if outcome.get("logo_asset_lock_applied") is True:
        repaired_sha256 = outcome.get("artifact_sha256")
        if not _is_sha256(repaired_sha256):
            raise RuntimeError("native logo asset-lock repaired artifact digest is invalid")
        evidence["logo_asset_lock_repaired_artifact_sha256"] = repaired_sha256
    if not evidence:
        raise RuntimeError("native reference receipt evidence is unavailable")
    return evidence


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _reference_bindings(review: ReferenceConsistencyReview) -> list[dict[str, object]]:
    if len(review.reference_sha256s) != len(review.reference_roles):
        raise RuntimeError("native reference review role/hash cardinality mismatch")
    return [
        {"order": index, "role": role, "sha256": digest}
        for index, (role, digest) in enumerate(
            zip(review.reference_roles, review.reference_sha256s, strict=True), start=1
        )
    ]


class ReceiptBoundNativeReferenceManagedDesktopVideoRuntime(
    NativeReferenceVerifiedManagedDesktopVideoRuntime
):
    """Preserve native-reference acceptance evidence through final receipts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("consistency_reviewer") is None:
            api_key = kwargs.get("api_key")
            if not isinstance(api_key, str) or not api_key.strip():
                raise RuntimeError("native reference consistency reviewer requires API credentials")
            kwargs["consistency_reviewer"] = OpenRouterReferenceConsistencyReviewer(
                api_key,
                _NATIVE_CONSISTENCY_MODEL_ID,
            )
        super().__init__(*args, **kwargs)
        self._native_receipt_context: ContextVar[dict[str, object] | None] = ContextVar(
            f"native-reference-receipt-{id(self)}",
            default=None,
        )

    def _record_consistency_evidence(
        self,
        *,
        request_id: str,
        job_id: str,
        review: ReferenceConsistencyReview,
        asset_lock_result: LogoAssetLockResult | None,
    ) -> dict[str, object]:
        evidence = super()._record_consistency_evidence(
            request_id=request_id,
            job_id=job_id,
            review=review,
            asset_lock_result=asset_lock_result,
        )
        bindings = _reference_bindings(review)
        document = {
            "schema": "ilaios.video.native-reference-review-binding.v1",
            "request_id": request_id,
            "job_id": job_id,
            "reviewer_id": review.reviewer_id,
            "criteria_version": review.criteria_version,
            "score": review.score,
            "threshold": review.threshold,
            "repair_target": review.repair_target,
            "reference_bindings": bindings,
            "interior_frame_sha256s": list(review.frame_sha256s),
            "first_frame_sha256": review.first_frame_sha256,
            "last_frame_sha256": review.last_frame_sha256,
            "parent_consistency_evidence_digest": evidence[
                "reference_consistency_evidence_digest"
            ],
            "passed": review.passed,
        }
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifact = self._evidence.put_artifact(body)
        provenance = self._evidence.append_provenance(
            job_id,
            artifact,
            "video.reference_consistency_binding",
        )
        evidence.update(
            {
                "reference_consistency_criteria_version": review.criteria_version,
                "reference_consistency_reference_bindings": bindings,
                "reference_consistency_frame_sha256s": review.frame_sha256s,
                "reference_consistency_first_frame_sha256": review.first_frame_sha256,
                "reference_consistency_last_frame_sha256": review.last_frame_sha256,
                "reference_consistency_binding_evidence_digest": artifact.digest,
                "reference_consistency_binding_provenance_hash": provenance.record_hash,
            }
        )
        return evidence

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        outcome = super()._generate_finished_product(
            run_root=run_root,
            request_id=request_id,
            job_id=job_id,
            objective=objective,
            duration_seconds=duration_seconds,
        )
        artifact_sha256 = outcome.get("artifact_sha256")
        if not _is_sha256(artifact_sha256):
            raise RuntimeError("native reference final artifact digest is invalid")
        binding_digest = outcome.get("reference_consistency_binding_evidence_digest")
        if not _is_sha256(binding_digest):
            raise RuntimeError("native reference consistency binding evidence is invalid")
        document = {
            "schema": "ilaios.video.native-reference-final-artifact-binding.v1",
            "request_id": request_id,
            "job_id": job_id,
            "artifact_sha256": artifact_sha256,
            "criteria_version": outcome.get("reference_consistency_criteria_version"),
            "score": outcome.get("reference_consistency_score"),
            "threshold": outcome.get("reference_consistency_threshold"),
            "reference_bindings": outcome.get("reference_consistency_reference_bindings"),
            "interior_frame_sha256s": outcome.get("reference_consistency_frame_sha256s"),
            "first_frame_sha256": outcome.get("reference_consistency_first_frame_sha256"),
            "last_frame_sha256": outcome.get("reference_consistency_last_frame_sha256"),
            "provider_native_reference_sha256s": outcome.get("native_reference_sha256s"),
            "review_binding_evidence_digest": binding_digest,
            "passed": outcome.get("reference_consistency_passed") is True,
        }
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifact = self._evidence.put_artifact(body)
        provenance = self._evidence.append_provenance(
            job_id,
            artifact,
            "video.native_reference_final_artifact_binding",
        )
        outcome["reference_consistency_final_artifact_evidence_digest"] = artifact.digest
        outcome["reference_consistency_final_artifact_provenance_hash"] = provenance.record_hash
        self._native_receipt_context.set(native_receipt_evidence(outcome))
        return outcome

    def execute(
        self,
        *,
        request_id: str,
        job_id: str,
        grant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        token = self._native_receipt_context.set(None)
        try:
            result = super().execute(
                request_id=request_id,
                job_id=job_id,
                grant_id=grant_id,
                now=now,
            )
            native_evidence = self._native_receipt_context.get()
            if not native_evidence:
                raise RuntimeError("native reference final receipt evidence is unavailable")
            qa = result.get("qa")
            if not isinstance(qa, dict) or qa.get("passed") is not True:
                raise RuntimeError("native reference canonical QA is unavailable")
            merged_qa = dict(qa)
            merged_qa.update(native_evidence)
            merged_result = dict(result)
            merged_result["qa"] = merged_qa
            merged_result.update(native_evidence)
            return merged_result
        finally:
            self._native_receipt_context.reset(token)
