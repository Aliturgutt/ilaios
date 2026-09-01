from __future__ import annotations

from datetime import datetime, timezone

from src.core.audit_engine import AuditEngine
from src.core.evidence_chain import EvidenceChain
from src.video_automation.audit_evidence import VideoAuditEvidenceRecorder


def test_video_event_is_written_to_audit_and_evidence_with_job_traceability() -> None:
    audit = AuditEngine()
    evidence = EvidenceChain()
    recorder = VideoAuditEvidenceRecorder(audit, evidence)
    timestamp = datetime.now(timezone.utc)
    audit_record, evidence_record = recorder.record(
        job_id="job-1",
        action="render_completed",
        status="success",
        details={"artifact_id": "artifact-1"},
        timestamp=timestamp,
    )
    assert audit_record.details["job_id"] == "job-1"
    assert audit_record.details["artifact_id"] == "artifact-1"
    assert evidence_record.source == "video_automation:job-1:render_completed"
    assert evidence.verify_integrity() is True


def test_multiple_events_form_one_integrity_checked_chain() -> None:
    audit = AuditEngine()
    evidence = EvidenceChain()
    recorder = VideoAuditEvidenceRecorder(audit, evidence)
    recorder.record(job_id="job-1", action="created", status="success")
    recorder.record(job_id="job-1", action="validated", status="success")
    records = evidence.get_records()
    assert records[1].prev_hash == records[0].chain_hash
    assert evidence.verify_integrity() is True
