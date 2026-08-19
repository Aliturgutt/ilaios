"""Evidence-preserving native-reference Desktop Video runtime.

The canonical provider runtime deliberately knows nothing about native-reference
specific QA fields. This additive adapter captures only already-verified native
provider/consistency/logo-lock evidence produced by
``NativeReferenceVerifiedManagedDesktopVideoRuntime`` and carries it into the
canonical ``qa``/result document returned to ProductRuntime. It does not change
provider routing, generation, thresholds, cost policy, or acceptance decisions.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

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
    if not evidence:
        raise RuntimeError("native reference receipt evidence is unavailable")
    return evidence


class ReceiptBoundNativeReferenceManagedDesktopVideoRuntime(
    NativeReferenceVerifiedManagedDesktopVideoRuntime
):
    """Preserve native-reference acceptance evidence through final receipts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._native_receipt_context: ContextVar[dict[str, object] | None] = ContextVar(
            f"native-reference-receipt-{id(self)}",
            default=None,
        )

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
