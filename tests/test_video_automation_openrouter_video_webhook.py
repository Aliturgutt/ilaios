from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import pytest

from src.video_automation.openrouter_video_webhook import (
    OpenRouterVideoWebhookStore,
    OpenRouterVideoWebhookVerifier,
    OpenRouterWebhookError,
)


class _Clock:
    def __init__(self, value: float = 1_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _body(
    *,
    job_id: str = "provider-job-001",
    status: str = "completed",
) -> bytes:
    event_type = f"video.generation.{status}"
    return json.dumps(
        {
            "type": event_type,
            "created_at": "2026-08-14T12:00:00.000Z",
            "data": {
                "id": job_id,
                "status": status,
                "generation_id": "generation-001",
                "model": "bytedance/seedance-2.0",
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _signature(secret: str, timestamp: int, raw_body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        str(timestamp).encode("ascii") + b"," + raw_body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_valid_signature_preserves_exact_raw_body_and_records_known_job(
    tmp_path: Path,
) -> None:
    clock = _Clock()
    secret = "webhook-secret"
    raw_body = _body()
    verifier = OpenRouterVideoWebhookVerifier(secret, clock=clock)
    event = verifier.verify(
        raw_body=raw_body,
        signature_header=_signature(secret, 1000, raw_body),
        idempotency_key="provider-job-001-completed",
    )
    store = OpenRouterVideoWebhookStore(tmp_path)
    store.register_job(request_id="request-001", provider_job_id="provider-job-001")

    record = store.record(event, recorded_at_epoch_s=1001.0)

    assert record.request_id == "request-001"
    assert record.provider_status == "completed"
    assert record.raw_body_sha256 == hashlib.sha256(raw_body).hexdigest()
    assert not record.duplicate


def test_duplicate_webhook_delivery_is_idempotent(tmp_path: Path) -> None:
    secret = "webhook-secret"
    raw_body = _body()
    event = OpenRouterVideoWebhookVerifier(
        secret, clock=_Clock()
    ).verify(
        raw_body=raw_body,
        signature_header=_signature(secret, 1000, raw_body),
        idempotency_key="same-delivery",
    )
    store = OpenRouterVideoWebhookStore(tmp_path)
    store.register_job(request_id="request-001", provider_job_id="provider-job-001")

    first = store.record(event, recorded_at_epoch_s=1001.0)
    second = store.record(event, recorded_at_epoch_s=1002.0)

    assert not first.duplicate
    assert second.duplicate
    assert second.raw_body_sha256 == first.raw_body_sha256


def test_unknown_job_callback_is_rejected(tmp_path: Path) -> None:
    secret = "webhook-secret"
    raw_body = _body(job_id="unknown-job")
    event = OpenRouterVideoWebhookVerifier(secret, clock=_Clock()).verify(
        raw_body=raw_body,
        signature_header=_signature(secret, 1000, raw_body),
        idempotency_key="unknown-delivery",
    )

    with pytest.raises(OpenRouterWebhookError, match="unknown provider job"):
        OpenRouterVideoWebhookStore(tmp_path).record(event)


def test_stale_or_wrong_signature_fails_closed() -> None:
    secret = "webhook-secret"
    raw_body = _body()
    verifier = OpenRouterVideoWebhookVerifier(secret, clock=_Clock(1400.0))

    with pytest.raises(OpenRouterWebhookError, match="timestamp is stale"):
        verifier.verify(
            raw_body=raw_body,
            signature_header=_signature(secret, 1000, raw_body),
            idempotency_key="stale",
        )

    verifier = OpenRouterVideoWebhookVerifier(secret, clock=_Clock(1000.0))
    with pytest.raises(OpenRouterWebhookError, match="signature is invalid"):
        verifier.verify(
            raw_body=raw_body,
            signature_header=_signature("wrong-secret", 1000, raw_body),
            idempotency_key="wrong",
        )


def test_idempotency_key_cannot_be_reused_for_different_material(tmp_path: Path) -> None:
    secret = "webhook-secret"
    verifier = OpenRouterVideoWebhookVerifier(secret, clock=_Clock())
    first_body = _body(status="completed")
    second_body = _body(status="failed")
    first = verifier.verify(
        raw_body=first_body,
        signature_header=_signature(secret, 1000, first_body),
        idempotency_key="same-key",
    )
    second = verifier.verify(
        raw_body=second_body,
        signature_header=_signature(secret, 1000, second_body),
        idempotency_key="same-key",
    )
    store = OpenRouterVideoWebhookStore(tmp_path)
    store.register_job(request_id="request-001", provider_job_id="provider-job-001")
    store.record(first)

    with pytest.raises(OpenRouterWebhookError, match="different webhook material"):
        store.record(second)


def test_event_type_and_status_must_match() -> None:
    secret = "webhook-secret"
    raw_body = json.dumps(
        {
            "type": "video.generation.completed",
            "created_at": "2026-08-14T12:00:00Z",
            "data": {"id": "job", "status": "failed"},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    verifier = OpenRouterVideoWebhookVerifier(secret, clock=_Clock())

    with pytest.raises(OpenRouterWebhookError, match="does not match status"):
        verifier.verify(
            raw_body=raw_body,
            signature_header=_signature(secret, 1000, raw_body),
            idempotency_key="mismatch",
        )
