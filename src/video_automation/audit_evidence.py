"""Canonical M29 integration with core Audit Engine and Evidence Chain."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from src.core.audit_engine import AuditEngine, AuditRecord
from src.core.evidence_chain import EvidenceChain, EvidenceRecord


class VideoAuditEvidenceError(ValueError):
    """Raised when a video audit/evidence event is invalid."""


class VideoAuditEvidenceRecorder:
    """Record job-traceable video events in both core audit and evidence systems."""

    def __init__(self, audit: AuditEngine, evidence: EvidenceChain) -> None:
        self._audit = audit
        self._evidence = evidence

    def record(
        self,
        *,
        job_id: str,
        action: str,
        status: str,
        details: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> tuple[AuditRecord, EvidenceRecord]:
        if not job_id or job_id != job_id.strip():
            raise VideoAuditEvidenceError("job_id must be non-blank and trimmed")
        event_time = timestamp or datetime.now(timezone.utc)
        payload_details = {"job_id": job_id, **(details or {})}
        audit_record = self._audit.record(
            "video_automation",
            action,
            status,
            payload_details,
            timestamp=event_time,
        )
        canonical_payload = "|".join(
            [job_id, action, status]
            + [f"{key}={payload_details[key]}" for key in sorted(payload_details)]
        )
        data_hash = sha256(canonical_payload.encode("utf-8")).hexdigest()
        existing = self._evidence.get_records()
        record = EvidenceRecord(
            timestamp=event_time,
            source=f"video_automation:{job_id}:{action}",
            data_hash=data_hash,
            prev_hash=None if not existing else existing[-1].chain_hash,
        )
        self._evidence.add_record(record)
        return audit_record, record
