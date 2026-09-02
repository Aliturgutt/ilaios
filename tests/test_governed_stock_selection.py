from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.video_automation.governed_stock_selection import (
    GovernedStockSelectionError,
    GovernedStockSelector,
)
from src.video_automation.stock_source_adapters import (
    RateLimitState,
    SourceProvenance,
    StockAssetCandidate,
    StockProvider,
    StockSearchRequest,
    StockSearchResult,
    StockSourceError,
)


@dataclass
class _Adapter:
    provider: StockProvider
    candidates: tuple[StockAssetCandidate, ...] = ()
    error: str | None = None
    calls: int = 0

    def search(self, request: StockSearchRequest) -> StockSearchResult:
        self.calls += 1
        if request.provider is not self.provider:
            raise StockSourceError("provider mismatch")
        if self.error is not None:
            raise StockSourceError(self.error)
        return StockSearchResult(
            request=request,
            candidates=self.candidates,
            rate_limit=RateLimitState(remaining=None, reset_at_iso8601=None),
        )


def _candidate(
    provider: StockProvider,
    *,
    media_type: str = "video",
    asset_id: str = "asset-1",
) -> StockAssetCandidate:
    return StockAssetCandidate(
        media_url="https://media.example.test/asset",
        preview_url=None,
        media_type=media_type,
        width=1920,
        height=1080,
        provenance=SourceProvenance(
            provider=provider,
            source_url="https://source.example.test/asset",
            asset_id=asset_id,
            creator="Creator",
            license_name="Example License",
            license_url="https://source.example.test/license",
            attribution_required=True,
            retrieved_at_iso8601="2026-09-02T00:00:00+00:00",
        ),
    )


def test_selector_uses_explicit_provider_order_and_preserves_attempts() -> None:
    pexels = _Adapter(StockProvider.PEXELS)
    wikimedia = _Adapter(
        StockProvider.WIKIMEDIA,
        candidates=(_candidate(StockProvider.WIKIMEDIA),),
    )
    selector = GovernedStockSelector(
        {
            StockProvider.PEXELS: pexels,
            StockProvider.WIKIMEDIA: wikimedia,
        },
        provider_order=(StockProvider.PEXELS, StockProvider.WIKIMEDIA),
    )

    selection = selector.select(
        tenant_id="tenant-1",
        job_id="job-1",
        query="enterprise automation",
    )

    assert selection.candidate.provenance.provider is StockProvider.WIKIMEDIA
    assert [(attempt.provider, attempt.status) for attempt in selection.attempts] == [
        (StockProvider.PEXELS, "empty"),
        (StockProvider.WIKIMEDIA, "selected"),
    ]
    assert pexels.calls == 1
    assert wikimedia.calls == 1


def test_selector_skips_unconfigured_provider_but_records_it() -> None:
    wikimedia = _Adapter(
        StockProvider.WIKIMEDIA,
        candidates=(_candidate(StockProvider.WIKIMEDIA),),
    )
    selector = GovernedStockSelector(
        {StockProvider.WIKIMEDIA: wikimedia},
        provider_order=(StockProvider.PEXELS, StockProvider.WIKIMEDIA),
    )

    selection = selector.select(
        tenant_id="tenant-1",
        job_id="job-1",
        query="earth",
    )

    assert selection.attempts[0].provider is StockProvider.PEXELS
    assert selection.attempts[0].status == "not_configured"
    assert selection.attempts[1].status == "selected"


def test_selector_fails_closed_on_provider_error_without_trying_next() -> None:
    pexels = _Adapter(StockProvider.PEXELS, error="network failed")
    wikimedia = _Adapter(
        StockProvider.WIKIMEDIA,
        candidates=(_candidate(StockProvider.WIKIMEDIA),),
    )
    selector = GovernedStockSelector(
        {
            StockProvider.PEXELS: pexels,
            StockProvider.WIKIMEDIA: wikimedia,
        },
        provider_order=(StockProvider.PEXELS, StockProvider.WIKIMEDIA),
    )

    with pytest.raises(GovernedStockSelectionError, match="pexels stock provider failed closed"):
        selector.select(
            tenant_id="tenant-1",
            job_id="job-1",
            query="enterprise automation",
        )

    assert pexels.calls == 1
    assert wikimedia.calls == 0


def test_selector_filters_media_type_without_weakening_provenance() -> None:
    pexels = _Adapter(
        StockProvider.PEXELS,
        candidates=(_candidate(StockProvider.PEXELS, media_type="image"),),
    )
    wikimedia = _Adapter(
        StockProvider.WIKIMEDIA,
        candidates=(_candidate(StockProvider.WIKIMEDIA, media_type="video"),),
    )
    selector = GovernedStockSelector(
        {
            StockProvider.PEXELS: pexels,
            StockProvider.WIKIMEDIA: wikimedia,
        },
        provider_order=(StockProvider.PEXELS, StockProvider.WIKIMEDIA),
    )

    selection = selector.select(
        tenant_id="tenant-1",
        job_id="job-1",
        query="enterprise automation",
        media_types=frozenset({"video"}),
    )

    assert selection.candidate.media_type == "video"
    assert selection.candidate.provenance.provider is StockProvider.WIKIMEDIA
    assert selection.attempts[0].status == "empty"


def test_selector_rejects_duplicate_provider_order() -> None:
    with pytest.raises(GovernedStockSelectionError, match="must not contain duplicates"):
        GovernedStockSelector(
            {},
            provider_order=(StockProvider.PEXELS, StockProvider.PEXELS),
        )
