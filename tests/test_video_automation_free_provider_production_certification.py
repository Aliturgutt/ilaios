from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from src.video_automation.free_provider_production_certification import (
    FreeProviderCertificationError,
    build_free_certification_request,
    free_model_candidates,
    mp4_signature_ok,
    run_free_certification,
)
from src.video_automation.openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)

SENTINEL_API_KEY = "literal-openrouter-credential-value-123"


class _Transport(OpenRouterTransport):
    def __init__(self, *, reported_cost: float = 0.0) -> None:
        self.reported_cost = reported_cost
        self.post_calls: list[
            tuple[str, Mapping[str, str], Mapping[str, object], float]
        ] = []
        self.get_calls: list[tuple[str, Mapping[str, str], float]] = []
        self.byte_calls: list[tuple[str, Mapping[str, str], float]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.post_calls.append((url, headers, body, timeout_seconds))
        return OpenRouterJsonResponse(202, {"id": "job-free-001", "status": "pending"})

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.get_calls.append((url, headers, timeout_seconds))
        if url.endswith("/videos/models"):
            return OpenRouterJsonResponse(
                200,
                {
                    "data": [
                        {
                            "id": SEEDANCE_FREE_MODEL_ID,
                            "pricing_skus": {"per-video-second": "0"},
                        }
                    ]
                },
            )
        return OpenRouterJsonResponse(
            200,
            {
                "id": "job-free-001",
                "status": "completed",
                "usage": {"cost": self.reported_cost},
            },
        )

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        self.byte_calls.append((url, headers, timeout_seconds))
        return OpenRouterByteResponse(
            200,
            b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2",
            "video/mp4",
            "https://openrouter.ai/api/v1/videos/job-free-001/content",
        )


def test_candidate_policy_rejects_any_nonfree_model() -> None:
    assert free_model_candidates(None)[0] == SEEDANCE_FREE_MODEL_ID
    with pytest.raises(FreeProviderCertificationError, match="forbids paid"):
        free_model_candidates("bytedance/seedance-2.0-fast")


def test_request_is_bound_to_explicit_free_model() -> None:
    request = build_free_certification_request(
        model_id=SEEDANCE_FREE_MODEL_ID,
        run_id="123",
        run_attempt="1",
        candidate_index=1,
    )
    assert request.provider_name == "openrouter-video-free"
    assert request.payload["model_id"] == SEEDANCE_FREE_MODEL_ID
    with pytest.raises(FreeProviderCertificationError, match="forbids paid"):
        build_free_certification_request(
            model_id="bytedance/seedance-2.0-fast",
            run_id="123",
            run_attempt="1",
            candidate_index=1,
        )


def test_real_free_proof_path_requires_zero_reported_cost(tmp_path: Path) -> None:
    transport = _Transport(reported_cost=0.0)
    receipt = run_free_certification(
        api_key=SENTINEL_API_KEY,
        proof_dir=tmp_path,
        revision_sha="a" * 40,
        run_id="123",
        run_attempt="1",
        candidate_models=(SEEDANCE_FREE_MODEL_ID,),
        transport=transport,
        monotonic=lambda: 0.0,
        sleep=lambda _: None,
    )
    assert receipt["status"] == "PASS"
    assert receipt["selected_model"] == SEEDANCE_FREE_MODEL_ID
    assert receipt["provider_reported_cost_usd"] == 0.0
    assert receipt["paid_fallback_allowed"] is False
    assert len(transport.post_calls) == 1
    assert transport.post_calls[0][2]["model"] == SEEDANCE_FREE_MODEL_ID
    assert (tmp_path / "free-provider-proof.mp4").exists()
    evidence = (tmp_path / "free-provider-receipt.json").read_text(encoding="utf-8")
    assert SENTINEL_API_KEY not in evidence


def test_nonzero_provider_cost_fails_closed(tmp_path: Path) -> None:
    transport = _Transport(reported_cost=0.01)
    with pytest.raises(FreeProviderCertificationError, match="non-zero cost"):
        run_free_certification(
            api_key=SENTINEL_API_KEY,
            proof_dir=tmp_path,
            revision_sha="a" * 40,
            run_id="124",
            run_attempt="1",
            candidate_models=(SEEDANCE_FREE_MODEL_ID,),
            transport=transport,
            monotonic=lambda: 0.0,
            sleep=lambda _: None,
        )
    receipt = (tmp_path / "free-provider-receipt.json").read_text(encoding="utf-8")
    assert SENTINEL_API_KEY not in receipt
    assert '"status": "COST_POLICY_VIOLATION"' in receipt
    assert not (tmp_path / "free-provider-proof.mp4").exists()


def test_mp4_signature_gate() -> None:
    assert mp4_signature_ok(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00")
    assert not mp4_signature_ok(b"not-an-mp4")
