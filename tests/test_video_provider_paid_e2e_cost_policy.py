from __future__ import annotations

import inspect
from collections.abc import Mapping

from src.video_automation import provider_production_certification
from src.video_automation.commercial_admission import (
    CommercialAdmissionEngine,
    CommercialPricingPolicy,
    LockedVideoQuote,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)
from src.video_automation.generation_job_polling import ProviderJobStatus
from src.video_automation.openrouter_managed_video_runtime import (
    OpenRouterManagedVideoGenerationJobPoller,
    actual_cost_microusd_from_observation,
)
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)


class _Transport(OpenRouterTransport):
    def __init__(self, payload: dict[str, object]) -> None:
        self._response = OpenRouterJsonResponse(200, payload)

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        return self._response

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("paid POST is outside this cost-policy unit test")

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("asset retrieval is outside this cost-policy unit test")


def _quote() -> LockedVideoQuote:
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())
    return engine.create_locked_quote(
        quote_id="paid-e2e-quote",
        now_epoch_s=1_000,
        tax_profile=TaxProfile("TEST", "TEST", 0),
        pricing=ProviderPricingSnapshot(
            provider_name="openrouter-video-managed",
            model_id="paid-video-model",
            pricing_fingerprint="catalog-sha",
            observed_at_epoch_s=1_000,
            expires_at_epoch_s=1_300,
            estimated_job_cost_microusd=200_000,
            max_job_cost_microusd=200_000,
        ),
        costs=VideoCostEnvelope(provider_generation_microusd=200_000),
        duration_seconds=4,
        aggregate_generated_seconds=4,
        resolution="480p",
        shot_count=1,
    )


def test_paid_terminal_cost_may_be_positive() -> None:
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=_Transport(
            {
                "id": "job-paid-001",
                "status": "completed",
                "usage": {"cost": "0.170000"},
            }
        ),
    )

    observation = poller.poll("job-paid-001")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    assert actual_cost_microusd_from_observation(observation) == 170_000


def test_positive_paid_cost_passes_when_locked_economics_remain_safe() -> None:
    quote = _quote()
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())

    reconciliation = engine.reconcile(
        quote=quote,
        actual_provider_cost_microusd=170_000,
        actual_other_variable_cost_microusd=0,
    )

    assert reconciliation.provider_quarantined is False
    assert reconciliation.actual_provider_cost_microusd == 170_000
    assert reconciliation.actual_margin_bps >= quote.hard_min_margin_bps


def test_paid_cost_above_locked_ceiling_fails_closed() -> None:
    quote = _quote()
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())

    reconciliation = engine.reconcile(
        quote=quote,
        actual_provider_cost_microusd=200_001,
        actual_other_variable_cost_microusd=0,
    )

    assert reconciliation.provider_quarantined is True
    assert reconciliation.quarantine_reason is not None
    assert "locked provider ceiling" in reconciliation.quarantine_reason


def test_paid_certification_never_reintroduces_free_only_poller() -> None:
    source = inspect.getsource(provider_production_certification)

    assert "OpenRouterManagedVideoGenerationJobPoller" in source
    assert "OpenRouterVideoGenerationJobPoller(" not in source
    assert '"cost_mode": "COMMERCIAL_BOUNDED"' in source
    assert 'receipt["customer_quote"]' in source
    assert 'receipt["commercial_reconciliation"]' in source
