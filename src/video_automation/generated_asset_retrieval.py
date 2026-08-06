"""Provider-independent retrieval of generated media assets.

This module resolves generated asset references through provider-specific
retriever adapters, writes the returned bytes to deterministic local paths,
and records immutable retrieval evidence. It does not inspect media contents,
probe codecs, retry requests, select providers, or infer generation outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .generation_dispatch_planning import EpisodeGenerationDispatchPlan
from .generation_result_ingestion import (
    EpisodeGenerationResultManifest,
    GenerationResultAsset,
)


class GeneratedAssetRetrievalError(ValueError):
    """Raised when generated asset retrieval cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class AssetHttpResponse:
    """Minimal HTTP response used by URL-backed asset retrievers."""

    status_code: int
    body: bytes
    content_type: str
    final_url: str

    def __post_init__(self) -> None:
        if self.status_code <= 0:
            raise GeneratedAssetRetrievalError("status_code must be greater than zero")
        if not self.body:
            raise GeneratedAssetRetrievalError("body must not be empty")
        _require_non_blank("content_type", self.content_type)
        _require_non_blank("final_url", self.final_url)


class AssetHttpTransport(Protocol):
    """HTTP byte transport contract for URL-backed asset retrieval."""

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AssetHttpResponse:
        """Return bytes and response metadata for one URL."""


class UrllibAssetHttpTransport:
    """Standard-library HTTPS transport for generated asset downloads."""

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AssetHttpResponse:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status_code = int(response.status)
                body = response.read()
                content_type = response.headers.get_content_type()
                final_url = response.geturl()
        except HTTPError as exc:
            raise GeneratedAssetRetrievalError(
                f"asset HTTP request failed with status {exc.code}"
            ) from exc
        except URLError as exc:
            raise GeneratedAssetRetrievalError("asset HTTP request failed") from exc
        return AssetHttpResponse(status_code, body, content_type, final_url)


@dataclass(frozen=True, slots=True)
class GeneratedAssetPayload:
    """Provider-neutral bytes returned for one generated asset reference."""

    source_asset_id: str
    body: bytes
    content_type: str
    file_extension: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("source_asset_id", self.source_asset_id)
        if not self.body:
            raise GeneratedAssetRetrievalError("body must not be empty")
        _require_non_blank("content_type", self.content_type)
        _validate_file_extension(self.file_extension)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class GeneratedAssetRetriever(Protocol):
    """Provider-specific adapter contract for generated asset retrieval."""

    @property
    def provider_id(self) -> str:
        """Return the provider identifier handled by this retriever."""

    def retrieve(self, asset_id: str) -> GeneratedAssetPayload:
        """Retrieve one explicit generated asset reference."""


class GeneratedAssetRetrieverRegistry:
    """Deterministic registry of provider-specific asset retrievers."""

    def __init__(self, retrievers: tuple[GeneratedAssetRetriever, ...] = ()) -> None:
        self._retrievers: dict[str, GeneratedAssetRetriever] = {}
        for retriever in retrievers:
            self.register(retriever)

    def register(self, retriever: GeneratedAssetRetriever) -> None:
        provider_id = retriever.provider_id
        _require_non_blank("provider_id", provider_id)
        if provider_id in self._retrievers:
            raise GeneratedAssetRetrievalError(
                f"asset retriever already registered: {provider_id}"
            )
        self._retrievers[provider_id] = retriever

    def get(self, provider_id: str) -> GeneratedAssetRetriever:
        _require_non_blank("provider_id", provider_id)
        try:
            return self._retrievers[provider_id]
        except KeyError as exc:
            raise GeneratedAssetRetrievalError(
                f"asset retriever not registered: {provider_id}"
            ) from exc

    def list_provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._retrievers))


class HttpUrlGeneratedAssetRetriever:
    """Generic retriever for providers that expose generated assets by URL."""

    def __init__(
        self,
        provider_id: str,
        *,
        transport: AssetHttpTransport | None = None,
        timeout_seconds: float = 60.0,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        _require_non_blank("provider_id", provider_id)
        if timeout_seconds <= 0:
            raise GeneratedAssetRetrievalError(
                "timeout_seconds must be greater than zero"
            )
        self._provider_id = provider_id
        self._transport = transport or UrllibAssetHttpTransport()
        self._timeout_seconds = timeout_seconds
        self._headers = _freeze_metadata(headers or {})

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def retrieve(self, asset_id: str) -> GeneratedAssetPayload:
        _require_https_url("asset_id", asset_id)
        response = self._transport.get_bytes(
            asset_id,
            headers=self._headers,
            timeout_seconds=self._timeout_seconds,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise GeneratedAssetRetrievalError(
                f"asset HTTP request failed with status {response.status_code}"
            )
        extension = _extension_from_content_type(response.content_type)
        return GeneratedAssetPayload(
            source_asset_id=asset_id,
            body=response.body,
            content_type=response.content_type,
            file_extension=extension,
            metadata={"final_url": response.final_url},
        )


@dataclass(frozen=True, slots=True)
class RetrievedGenerationAsset:
    """Immutable local retrieval evidence for one generated asset."""

    asset_id: str
    dispatch_id: str
    provider_job_id: str
    provider_id: str
    batch_number: int
    output_index: int
    local_path: str
    sha256_hex: str
    byte_length: int
    content_type: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "asset_id",
            "dispatch_id",
            "provider_job_id",
            "provider_id",
            "local_path",
            "sha256_hex",
            "content_type",
        ):
            _require_non_blank(name, getattr(self, name))
        if self.batch_number <= 0:
            raise GeneratedAssetRetrievalError(
                "batch_number must be greater than zero"
            )
        if self.output_index <= 0:
            raise GeneratedAssetRetrievalError(
                "output_index must be greater than zero"
            )
        if self.byte_length <= 0:
            raise GeneratedAssetRetrievalError("byte_length must be greater than zero")
        if len(self.sha256_hex) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256_hex
        ):
            raise GeneratedAssetRetrievalError(
                "sha256_hex must be a lowercase SHA-256 digest"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class EpisodeGeneratedAssetRetrievalManifest:
    """Immutable retrieval evidence for one generation result manifest."""

    retrieval_manifest_id: str
    result_manifest_id: str
    dispatch_plan_id: str
    episode_id: str
    assets: tuple[RetrievedGenerationAsset, ...]
    asset_count: int
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "retrieval_manifest_id",
            "result_manifest_id",
            "dispatch_plan_id",
            "episode_id",
        ):
            _require_non_blank(name, getattr(self, name))
        if self.asset_count != len(self.assets):
            raise GeneratedAssetRetrievalError(
                "asset_count must equal assets length"
            )
        asset_ids = tuple(asset.asset_id for asset in self.assets)
        if len(asset_ids) != len(set(asset_ids)):
            raise GeneratedAssetRetrievalError("retrieved asset_ids must be unique")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class GeneratedAssetRetrievalCoordinator:
    """Retrieve result-manifest assets through explicit provider adapters."""

    def __init__(
        self,
        registry: GeneratedAssetRetrieverRegistry,
        storage_root: Path,
    ) -> None:
        self._registry = registry
        self._storage_root = storage_root

    def retrieve(
        self,
        result_manifest: EpisodeGenerationResultManifest,
        dispatch_plan: EpisodeGenerationDispatchPlan,
    ) -> EpisodeGeneratedAssetRetrievalManifest:
        _validate_manifest_matches_dispatch_plan(result_manifest, dispatch_plan)
        provider_by_dispatch = {
            dispatch.dispatch_id: dispatch.provider_id
            for dispatch in dispatch_plan.dispatches
        }
        self._storage_root.mkdir(parents=True, exist_ok=True)

        retrieved: list[RetrievedGenerationAsset] = []
        for asset in result_manifest.assets:
            provider_id = _provider_for_asset(asset, provider_by_dispatch)
            payload = self._registry.get(provider_id).retrieve(asset.asset_id)
            if payload.source_asset_id != asset.asset_id:
                raise GeneratedAssetRetrievalError(
                    "retrieved payload source_asset_id does not match requested asset_id"
                )
            retrieved.append(
                self._persist_asset(asset, provider_id, payload, len(retrieved) + 1)
            )

        canonical = _canonical_manifest_material(result_manifest, tuple(retrieved))
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return EpisodeGeneratedAssetRetrievalManifest(
            retrieval_manifest_id=f"asset-retrieval-{digest[:16]}",
            result_manifest_id=result_manifest.result_manifest_id,
            dispatch_plan_id=result_manifest.dispatch_plan_id,
            episode_id=result_manifest.episode_id,
            assets=tuple(retrieved),
            asset_count=len(retrieved),
            metadata={"storage_root": str(self._storage_root)},
        )

    def _persist_asset(
        self,
        asset: GenerationResultAsset,
        provider_id: str,
        payload: GeneratedAssetPayload,
        sequence_number: int,
    ) -> RetrievedGenerationAsset:
        body_sha = sha256(payload.body).hexdigest()
        identity = (
            f"{asset.asset_id}|{asset.dispatch_id}|{asset.output_index}|{body_sha}"
        )
        identity_sha = sha256(identity.encode("utf-8")).hexdigest()
        filename = (
            f"asset-{sequence_number:04d}-{identity_sha[:16]}{payload.file_extension}"
        )
        target = self._storage_root / filename
        _write_deterministically(target, payload.body, body_sha)
        metadata = dict(payload.metadata)
        metadata["source_asset_id"] = asset.asset_id
        return RetrievedGenerationAsset(
            asset_id=asset.asset_id,
            dispatch_id=asset.dispatch_id,
            provider_job_id=asset.provider_job_id,
            provider_id=provider_id,
            batch_number=asset.batch_number,
            output_index=asset.output_index,
            local_path=str(target),
            sha256_hex=body_sha,
            byte_length=len(payload.body),
            content_type=payload.content_type,
            metadata=metadata,
        )


def _validate_manifest_matches_dispatch_plan(
    result_manifest: EpisodeGenerationResultManifest,
    dispatch_plan: EpisodeGenerationDispatchPlan,
) -> None:
    if result_manifest.dispatch_plan_id != dispatch_plan.dispatch_plan_id:
        raise GeneratedAssetRetrievalError(
            "result manifest does not belong to dispatch plan"
        )
    if result_manifest.episode_id != dispatch_plan.episode_id:
        raise GeneratedAssetRetrievalError(
            "result manifest episode_id does not match dispatch plan"
        )


def _provider_for_asset(
    asset: GenerationResultAsset,
    provider_by_dispatch: Mapping[str, str],
) -> str:
    try:
        return provider_by_dispatch[asset.dispatch_id]
    except KeyError as exc:
        raise GeneratedAssetRetrievalError(
            f"unknown dispatch_id in result asset: {asset.dispatch_id}"
        ) from exc


def _write_deterministically(target: Path, body: bytes, expected_sha: str) -> None:
    if target.exists():
        if not target.is_file():
            raise GeneratedAssetRetrievalError(
                f"retrieval target is not a file: {target}"
            )
        if sha256(target.read_bytes()).hexdigest() != expected_sha:
            raise GeneratedAssetRetrievalError(
                f"retrieval target already exists with different content: {target}"
            )
        return
    temporary = target.with_name(f"{target.name}.part")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(body)
    temporary.replace(target)


def _extension_from_content_type(content_type: str) -> str:
    normalized = content_type.split(";", 1)[0].strip().lower()
    extensions = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "application/octet-stream": ".bin",
    }
    try:
        return extensions[normalized]
    except KeyError as exc:
        raise GeneratedAssetRetrievalError(
            f"unsupported generated asset content_type: {normalized}"
        ) from exc


def _require_https_url(name: str, value: str) -> None:
    _require_non_blank(name, value)
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise GeneratedAssetRetrievalError(f"{name} must be an absolute HTTPS URL")


def _validate_file_extension(extension: str) -> None:
    _require_non_blank("file_extension", extension)
    if not extension.startswith(".") or any(
        character in extension for character in ("/", "\\")
    ):
        raise GeneratedAssetRetrievalError("file_extension must be a simple suffix")


def _canonical_manifest_material(
    result_manifest: EpisodeGenerationResultManifest,
    assets: tuple[RetrievedGenerationAsset, ...],
) -> str:
    lines = [
        f"result_manifest_id={result_manifest.result_manifest_id}",
        f"dispatch_plan_id={result_manifest.dispatch_plan_id}",
        f"episode_id={result_manifest.episode_id}",
    ]
    lines.extend(
        f"asset_id={asset.asset_id}|provider_id={asset.provider_id}|"
        f"sha256={asset.sha256_hex}|bytes={asset.byte_length}|"
        f"local_path={asset.local_path}"
        for asset in assets
    )
    return "\n".join(lines)


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise GeneratedAssetRetrievalError(f"{name} must not be blank")
