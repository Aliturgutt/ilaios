from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from services.ai_governance import RoutingPolicy
from services.evidence import EvidenceStore
from services.openrouter_routing_sources import (
    OpenRouterCatalogSource,
    OpenRouterHTTPResponse,
    OpenRouterReadOnlyTransport,
    OpenRouterRuntimeSource,
    OpenRouterTelemetryError,
    build_openrouter_governed_routing_runtime,
)
from services.routing_intelligence import RoutingIntelligenceRequest

NOW = datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc)
SECRET = "test-openrouter-secret-never-persist"
MODEL_ID = "vendor/model-a"
CAPABILITIES = {MODEL_ID: frozenset({"text.reasoning"})}


class FakeTransport(OpenRouterReadOnlyTransport):
    def __init__(self, responses: list[OpenRouterHTTPResponse | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def get_json(
        self,
        url: str,
        *,
        api_key: str,
        timeout_seconds: float,
    ) -> OpenRouterHTTPResponse:
        assert api_key == SECRET
        assert timeout_seconds > 0
        self.calls.append(url)
        if not self._responses:
            raise AssertionError("unexpected OpenRouter telemetry request")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _secret_reader(name: str) -> str | None:
    assert name == "OPENROUTER_API_KEY"
    return SECRET


def _model(
    *,
    model_id: str = MODEL_ID,
    prompt: str = "0.000002",
    completion: str = "0.000004",
    context_length: int = 128_000,
    max_completion_tokens: int = 8_000,
) -> dict[str, object]:
    return {
        "id": model_id,
        "context_length": context_length,
        "pricing": {
            "prompt": prompt,
            "completion": completion,
            "request": "0",
        },
        "top_provider": {"max_completion_tokens": max_completion_tokens},
    }


def _catalog_response(*models: Mapping[str, object], latency_ms: int = 40) -> OpenRouterHTTPResponse:
    return OpenRouterHTTPResponse(200, {"data": [dict(model) for model in models]}, latency_ms)


def _key_response(
    limit_remaining: object,
    *,
    latency_ms: int = 20,
) -> OpenRouterHTTPResponse:
    return OpenRouterHTTPResponse(
        200,
        {
            "data": {
                "limit": 10,
                "limit_remaining": limit_remaining,
                "usage": 1,
                "is_free_tier": False,
            }
        },
        latency_ms,
    )


def test_catalog_uses_only_configured_models_and_live_pricing() -> None:
    transport = FakeTransport(
        [
            _catalog_response(
                _model(),
                _model(model_id="unconfigured/rogue", prompt="0", completion="0"),
            )
        ]
    )
    source = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )

    snapshot = source.observe_catalog(now=NOW)

    assert len(snapshot.providers) == 1
    assert snapshot.providers[0].provider_id == "openrouter"
    assert [item.model_id for item in snapshot.models] == [MODEL_ID]
    model = snapshot.models[0]
    assert model.capabilities == frozenset({"text.reasoning"})
    assert model.input_cost_per_million == Decimal("2")
    assert model.output_cost_per_million == Decimal("4")
    assert model.context_window == 128_000
    assert model.max_output_tokens == 8_000
    assert snapshot.catalog_version.startswith("openrouter:")


def test_catalog_cache_is_bounded_and_does_not_refetch_inside_ttl() -> None:
    transport = FakeTransport([_catalog_response(_model())])
    source = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
        ttl_seconds=60,
    )

    first = source.observe_catalog(now=NOW)
    second = source.observe_catalog(now=NOW + timedelta(seconds=30))

    assert first is second
    assert len(transport.calls) == 1


def test_catalog_missing_or_nonfinite_price_fails_closed() -> None:
    missing = _model()
    pricing = missing["pricing"]
    assert isinstance(pricing, dict)
    del pricing["prompt"]
    missing_transport = FakeTransport([_catalog_response(missing)])
    missing_source = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=missing_transport,
        secret_reader=_secret_reader,
    )
    with pytest.raises(OpenRouterTelemetryError, match="pricing is missing"):
        missing_source.observe_catalog(now=NOW)

    nan_transport = FakeTransport(
        [_catalog_response(_model(prompt="NaN"))]
    )
    nan_source = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=nan_transport,
        secret_reader=_secret_reader,
    )
    with pytest.raises(OpenRouterTelemetryError, match="must be finite"):
        nan_source.observe_catalog(now=NOW)


def test_authenticated_catalog_cannot_widen_configured_model_set() -> None:
    transport = FakeTransport(
        [
            _catalog_response(
                _model(),
                _model(model_id="vendor/unapproved", prompt="0.000001", completion="0.000001"),
            )
        ]
    )
    source = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )

    snapshot = source.observe_catalog(now=NOW)

    assert {item.model_id for item in snapshot.models} == {MODEL_ID}
    assert snapshot.models[0].capabilities == CAPABILITIES[MODEL_ID]


def test_runtime_converts_live_credit_remaining_to_conservative_token_quota() -> None:
    transport = FakeTransport(
        [
            _catalog_response(_model()),
            _key_response("1.00"),
        ]
    )
    catalog = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )
    runtime = OpenRouterRuntimeSource(
        catalog,
        transport=transport,
        secret_reader=_secret_reader,
    )

    catalog.observe_catalog(now=NOW)
    snapshot = runtime.observe_runtime(now=NOW)

    quota = snapshot.quota_for("openrouter")
    assert quota is not None
    # Worst configured live token price is $0.000004, so $1.00 is bounded
    # conservatively to 250,000 tokens.
    assert quota.remaining_tokens == 250_000
    assert quota.remaining_requests is None
    health = snapshot.health_for("openrouter")
    assert health is not None
    assert health.success_rate == Decimal(1)
    assert health.p95_latency_ms == 40
    assert health.circuit_open is False


def test_zero_cost_catalog_does_not_fake_credit_exhaustion() -> None:
    transport = FakeTransport(
        [
            _catalog_response(_model(prompt="0", completion="0")),
            _key_response("0"),
        ]
    )
    catalog = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )
    runtime = OpenRouterRuntimeSource(
        catalog,
        transport=transport,
        secret_reader=_secret_reader,
    )

    catalog.observe_catalog(now=NOW)
    snapshot = runtime.observe_runtime(now=NOW)

    quota = snapshot.quota_for("openrouter")
    assert quota is not None
    assert quota.remaining_tokens is None


def test_paid_catalog_with_zero_live_credit_fails_routing_quota() -> None:
    transport = FakeTransport(
        [
            _catalog_response(_model()),
            _key_response("0"),
        ]
    )
    runtime = build_openrouter_governed_routing_runtime(
        evidence_root=Path("unused-test-evidence"),
        model_capabilities=CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )

    try:
        with pytest.raises(Exception, match="no candidate"):
            runtime.resolve(
                execution_id="quota-zero",
                policy=RoutingPolicy(allowed_models=frozenset({MODEL_ID})),
                request=RoutingIntelligenceRequest("text.reasoning", 100, 50),
                now=NOW,
            )
    finally:
        import shutil

        shutil.rmtree("unused-test-evidence", ignore_errors=True)


def test_auth_failure_fails_closed_without_secret_disclosure() -> None:
    transport = FakeTransport([OpenRouterHTTPResponse(401, {}, 12)])
    source = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )

    with pytest.raises(OpenRouterTelemetryError) as raised:
        source.observe_catalog(now=NOW)

    assert "authentication failed" in str(raised.value)
    assert SECRET not in str(raised.value)


def test_transport_failure_is_not_replaced_with_optimistic_state() -> None:
    transport = FakeTransport([OpenRouterTelemetryError("telemetry transport failed")])
    source = OpenRouterCatalogSource(
        CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )

    with pytest.raises(OpenRouterTelemetryError, match="transport failed"):
        source.observe_catalog(now=NOW)


def test_governed_runtime_uses_live_sources_and_persists_sanitized_evidence(
    tmp_path: Path,
) -> None:
    transport = FakeTransport(
        [
            _catalog_response(_model(), latency_ms=31),
            _key_response("2.00", latency_ms=19),
        ]
    )
    evidence_root = tmp_path / "routing-evidence"
    runtime = build_openrouter_governed_routing_runtime(
        evidence_root=evidence_root,
        model_capabilities=CAPABILITIES,
        transport=transport,
        secret_reader=_secret_reader,
    )

    resolution = runtime.resolve(
        execution_id="live-openrouter-routing-proof",
        policy=RoutingPolicy(allowed_models=frozenset({MODEL_ID})),
        request=RoutingIntelligenceRequest("text.reasoning", 1_000, 500),
        now=NOW,
    )

    assert resolution.selected_model.model_id == MODEL_ID
    assert resolution.selected_model.provider_id == "openrouter"
    assert len(transport.calls) == 2
    store = EvidenceStore(evidence_root)
    payload = store.get_artifact(resolution.artifact_digest)
    decoded = json.loads(payload.decode("utf-8"))
    assert decoded["selected"] == {
        "model_id": MODEL_ID,
        "provider_id": "openrouter",
    }
    assert decoded["catalog"]["models"][0]["input_cost_per_million"] == "2.000000"
    assert decoded["runtime_state"]["quota"][0]["remaining_tokens"] == 500_000
    assert SECRET.encode("utf-8") not in payload
    verified = store.verify()
    assert verified[-1].record_hash == resolution.provenance_hash
