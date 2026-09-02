"""Governed stock-media selection for the canonical Video Factory.

This module composes the already-existing provider-bound stock adapters without
creating a second router or bypassing provider provenance. Selection is explicit,
deterministic, and fail-closed: provider contract/network failures stop the
selection; only a successful empty result may advance to the next configured
provider. Every attempted provider is retained in the returned evidence object.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.video_automation.stock_source_adapters import (
    GovernedStockSourceAdapter,
    StockAssetCandidate,
    StockProvider,
    StockSearchRequest,
    StockSourceError,
)


class GovernedStockSelectionError(ValueError):
    """Raised when governed stock selection cannot produce an admissible asset."""


DEFAULT_PROVIDER_ORDER: tuple[StockProvider, ...] = (
    StockProvider.PEXELS,
    StockProvider.PIXABAY,
    StockProvider.UNSPLASH,
    StockProvider.WIKIMEDIA,
    StockProvider.NASA,
    StockProvider.INTERNET_ARCHIVE,
)

_ALLOWED_MEDIA_TYPES = frozenset({"image", "video", "audio"})


@dataclass(frozen=True, slots=True)
class StockSelectionAttempt:
    provider: StockProvider
    status: str
    candidate_count: int


@dataclass(frozen=True, slots=True)
class GovernedStockSelection:
    candidate: StockAssetCandidate
    attempts: tuple[StockSelectionAttempt, ...]


class GovernedStockSelector:
    """Select one attributed stock asset through an explicit provider order."""

    def __init__(
        self,
        adapters: Mapping[StockProvider, GovernedStockSourceAdapter],
        *,
        provider_order: Sequence[StockProvider] = DEFAULT_PROVIDER_ORDER,
    ) -> None:
        resolved_order = tuple(provider_order)
        if not resolved_order:
            raise GovernedStockSelectionError("provider_order must not be empty")
        if len(set(resolved_order)) != len(resolved_order):
            raise GovernedStockSelectionError("provider_order must not contain duplicates")
        self._adapters = dict(adapters)
        self._provider_order = resolved_order

    def select(
        self,
        *,
        tenant_id: str,
        job_id: str,
        query: str,
        media_types: frozenset[str] = frozenset({"video", "image"}),
        max_results_per_provider: int = 10,
    ) -> GovernedStockSelection:
        if not media_types or not media_types <= _ALLOWED_MEDIA_TYPES:
            raise GovernedStockSelectionError(
                "media_types must be a non-empty subset of image, video, audio"
            )
        attempts: list[StockSelectionAttempt] = []
        configured_provider_seen = False

        for provider in self._provider_order:
            adapter = self._adapters.get(provider)
            if adapter is None:
                attempts.append(StockSelectionAttempt(provider, "not_configured", 0))
                continue
            configured_provider_seen = True
            request = StockSearchRequest(
                tenant_id=tenant_id,
                job_id=job_id,
                query=query,
                provider=provider,
                max_results=max_results_per_provider,
            )
            try:
                result = adapter.search(request)
            except StockSourceError as exc:
                raise GovernedStockSelectionError(
                    f"{provider.value} stock provider failed closed"
                ) from exc
            if result.request != request:
                raise GovernedStockSelectionError(
                    f"{provider.value} stock result request mismatch"
                )
            admissible = tuple(
                candidate
                for candidate in result.candidates
                if candidate.media_type in media_types
            )
            attempts.append(
                StockSelectionAttempt(provider, "selected" if admissible else "empty", len(result.candidates))
            )
            if admissible:
                return GovernedStockSelection(admissible[0], tuple(attempts))

        if not configured_provider_seen:
            raise GovernedStockSelectionError("no governed stock provider is configured")
        raise GovernedStockSelectionError("no admissible governed stock asset was returned")
