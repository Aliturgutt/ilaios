"""Canonical M13 persistent Asset Store and provenance registry.

M13 converts already-retrieved media evidence into registered MediaAsset
records. It verifies local paths and checksums, retains provider/source/job
provenance, persists records atomically, and exposes registered assets to
downstream consumers.

This module does not retrieve media, select providers, inspect media codecs,
perform technical validation, render media, or mutate upstream M12 evidence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import cast

from .generated_asset_retrieval import RetrievedGenerationAsset
from .models import MediaAsset, MediaType


class AssetStoreError(RuntimeError):
    """Raised when canonical asset registration cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class AssetProvenanceRecord:
    """Immutable provenance retained beside one registered MediaAsset."""

    asset: MediaAsset
    dispatch_id: str
    provider_job_id: str
    batch_number: int
    output_index: int

    def __post_init__(self) -> None:
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("provider_job_id", self.provider_job_id)

        if self.batch_number <= 0:
            raise AssetStoreError(
                "batch_number must be greater than zero"
            )

        if self.output_index <= 0:
            raise AssetStoreError(
                "output_index must be greater than zero"
            )


class PersistentAssetStore:
    """Deterministic JSON-backed registry of canonical MediaAsset records."""

    def __init__(self, registry_path: str | Path) -> None:
        path = Path(registry_path)

        if path.exists() and not path.is_file():
            raise AssetStoreError(
                f"registry_path must reference a file: {path}"
            )

        self._registry_path = path
        self._records: dict[str, AssetProvenanceRecord] = {}

        if path.exists():
            self._load()

    @property
    def registry_path(self) -> Path:
        """Return the configured registry path."""

        return self._registry_path

    def register_retrieved_asset(
        self,
        *,
        job_id: str,
        media_type: MediaType,
        retrieved: RetrievedGenerationAsset,
        validated: bool = False,
    ) -> MediaAsset:
        """Register one M12 retrieval result as a canonical MediaAsset."""

        _require_non_blank("job_id", job_id)

        source_reference = retrieved.metadata.get("source_asset_id")

        if source_reference is None:
            source_reference = retrieved.asset_id

        _require_non_blank(
            "source_reference",
            source_reference,
        )

        local_path = Path(retrieved.local_path)

        if not local_path.exists():
            raise AssetStoreError(
                f"retrieved asset file does not exist: {local_path}"
            )

        if not local_path.is_file():
            raise AssetStoreError(
                f"retrieved asset path is not a file: {local_path}"
            )

        try:
            body = local_path.read_bytes()
        except OSError as exc:
            raise AssetStoreError(
                f"retrieved asset file is not readable: {local_path}"
            ) from exc

        if not body:
            raise AssetStoreError(
                "retrieved asset file must not be empty"
            )

        actual_sha256 = sha256(body).hexdigest()

        if actual_sha256 != retrieved.sha256_hex:
            raise AssetStoreError(
                "retrieved asset checksum does not match file contents"
            )

        if len(body) != retrieved.byte_length:
            raise AssetStoreError(
                "retrieved asset byte_length does not match file contents"
            )

        asset = MediaAsset(
            asset_id=retrieved.asset_id,
            job_id=job_id,
            media_type=media_type,
            file_path=str(local_path.resolve()),
            checksum_sha256=actual_sha256,
            provider_name=retrieved.provider_id,
            source_reference=source_reference,
            validated=validated,
        )

        record = AssetProvenanceRecord(
            asset=asset,
            dispatch_id=retrieved.dispatch_id,
            provider_job_id=retrieved.provider_job_id,
            batch_number=retrieved.batch_number,
            output_index=retrieved.output_index,
        )

        existing = self._records.get(asset.asset_id)

        if existing is not None:
            if existing != record:
                raise AssetStoreError(
                    f"asset_id already registered with different evidence: "
                    f"{asset.asset_id}"
                )

            return existing.asset

        self._records[asset.asset_id] = record

        try:
            self._persist()
        except Exception:
            del self._records[asset.asset_id]
            raise

        return asset

    def get(self, asset_id: str) -> MediaAsset:
        """Return one registered canonical MediaAsset."""

        return self.get_record(asset_id).asset

    def get_record(self, asset_id: str) -> AssetProvenanceRecord:
        """Return one registered asset with its provenance."""

        _require_non_blank("asset_id", asset_id)

        try:
            return self._records[asset_id]
        except KeyError as exc:
            raise AssetStoreError(
                f"asset is not registered: {asset_id}"
            ) from exc

    def contains(self, asset_id: str) -> bool:
        """Return whether one asset identifier is registered."""

        _require_non_blank("asset_id", asset_id)
        return asset_id in self._records

    def list_asset_ids(self) -> tuple[str, ...]:
        """Return asset identifiers in deterministic sorted order."""

        return tuple(sorted(self._records))

    def list_assets(self) -> tuple[MediaAsset, ...]:
        """Return registered assets in deterministic identifier order."""

        return tuple(
            self._records[asset_id].asset
            for asset_id in self.list_asset_ids()
        )

    def require_registered_path(self, asset_id: str) -> Path:
        """Return a verified local path only for a registered asset.

        This method is the downstream boundary intended to replace uncontrolled
        direct filesystem paths.
        """

        asset = self.get(asset_id)
        path = Path(asset.file_path)

        if not path.exists() or not path.is_file():
            raise AssetStoreError(
                f"registered asset file is unavailable: {asset_id}"
            )

        try:
            actual_sha256 = sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise AssetStoreError(
                f"registered asset file is unreadable: {asset_id}"
            ) from exc

        if actual_sha256 != asset.checksum_sha256:
            raise AssetStoreError(
                f"registered asset checksum changed: {asset_id}"
            )

        return path

    def set_validation_state(
        self,
        asset_id: str,
        *,
        validated: bool,
    ) -> MediaAsset:
        """Persist an explicit validation-state transition for one asset."""

        existing = self.get_record(asset_id)
        asset = existing.asset

        if asset.validated is validated:
            return asset

        replacement_asset = MediaAsset(
            asset_id=asset.asset_id,
            job_id=asset.job_id,
            media_type=asset.media_type,
            file_path=asset.file_path,
            checksum_sha256=asset.checksum_sha256,
            provider_name=asset.provider_name,
            source_reference=asset.source_reference,
            validated=validated,
        )

        replacement_record = AssetProvenanceRecord(
            asset=replacement_asset,
            dispatch_id=existing.dispatch_id,
            provider_job_id=existing.provider_job_id,
            batch_number=existing.batch_number,
            output_index=existing.output_index,
        )

        self._records[asset_id] = replacement_record

        try:
            self._persist()
        except Exception:
            self._records[asset_id] = existing
            raise

        return replacement_asset

    def provenance_map(
        self,
    ) -> Mapping[str, AssetProvenanceRecord]:
        """Return an immutable deterministic provenance mapping."""

        return MappingProxyType(
            {
                asset_id: self._records[asset_id]
                for asset_id in self.list_asset_ids()
            }
        )

    def _persist(self) -> None:
        parent = self._registry_path.parent

        if parent != Path("."):
            parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema_version": 1,
            "assets": [
                _record_to_json(self._records[asset_id])
                for asset_id in self.list_asset_ids()
            ],
        }

        encoded = (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )

        temporary = self._registry_path.with_name(
            f"{self._registry_path.name}.tmp"
        )

        try:
            temporary.write_text(encoded, encoding="utf-8")
            temporary.replace(self._registry_path)
        except OSError as exc:
            if temporary.exists():
                temporary.unlink()
            raise AssetStoreError(
                f"failed to persist asset registry: {self._registry_path}"
            ) from exc

    def _load(self) -> None:
        try:
            raw = self._registry_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise AssetStoreError(
                f"failed to read asset registry: {self._registry_path}"
            ) from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AssetStoreError(
                "asset registry is not valid JSON"
            ) from exc

        if not isinstance(parsed, dict):
            raise AssetStoreError(
                "asset registry root must be an object"
            )

        schema_version = parsed.get("schema_version")

        if schema_version != 1:
            raise AssetStoreError(
                f"unsupported asset registry schema_version: "
                f"{schema_version}"
            )

        assets = parsed.get("assets")

        if not isinstance(assets, list):
            raise AssetStoreError(
                "asset registry assets must be a list"
            )

        loaded: dict[str, AssetProvenanceRecord] = {}

        for item in assets:
            if not isinstance(item, dict):
                raise AssetStoreError(
                    "asset registry item must be an object"
                )

            record = _record_from_json(
                cast(dict[str, object], item)
            )

            asset_id = record.asset.asset_id

            if asset_id in loaded:
                raise AssetStoreError(
                    f"duplicate asset_id in registry: {asset_id}"
                )

            loaded[asset_id] = record

        self._records = loaded


def _record_to_json(
    record: AssetProvenanceRecord,
) -> dict[str, object]:
    asset = record.asset

    return {
        "asset_id": asset.asset_id,
        "job_id": asset.job_id,
        "media_type": asset.media_type.value,
        "file_path": asset.file_path,
        "checksum_sha256": asset.checksum_sha256,
        "provider_name": asset.provider_name,
        "source_reference": asset.source_reference,
        "validated": asset.validated,
        "dispatch_id": record.dispatch_id,
        "provider_job_id": record.provider_job_id,
        "batch_number": record.batch_number,
        "output_index": record.output_index,
    }


def _record_from_json(
    item: dict[str, object],
) -> AssetProvenanceRecord:
    asset_id = _json_string(item, "asset_id")
    job_id = _json_string(item, "job_id")
    media_type_value = _json_string(item, "media_type")
    file_path = _json_string(item, "file_path")
    checksum_sha256 = _json_string(item, "checksum_sha256")
    provider_name = _json_string(item, "provider_name")
    source_reference = _json_string(item, "source_reference")
    validated = item.get("validated")
    dispatch_id = _json_string(item, "dispatch_id")
    provider_job_id = _json_string(item, "provider_job_id")
    batch_number = _json_int(item, "batch_number")
    output_index = _json_int(item, "output_index")

    if not isinstance(validated, bool):
        raise AssetStoreError(
            "asset registry validated must be boolean"
        )

    try:
        media_type = MediaType(media_type_value)
    except ValueError as exc:
        raise AssetStoreError(
            f"unsupported media_type in asset registry: "
            f"{media_type_value}"
        ) from exc

    return AssetProvenanceRecord(
        asset=MediaAsset(
            asset_id=asset_id,
            job_id=job_id,
            media_type=media_type,
            file_path=file_path,
            checksum_sha256=checksum_sha256,
            provider_name=provider_name,
            source_reference=source_reference,
            validated=validated,
        ),
        dispatch_id=dispatch_id,
        provider_job_id=provider_job_id,
        batch_number=batch_number,
        output_index=output_index,
    )


def _json_string(
    item: dict[str, object],
    key: str,
) -> str:
    value = item.get(key)

    if not isinstance(value, str):
        raise AssetStoreError(
            f"asset registry {key} must be a string"
        )

    _require_non_blank(key, value)
    return value


def _json_int(
    item: dict[str, object],
    key: str,
) -> int:
    value = item.get(key)

    if not isinstance(value, int) or isinstance(value, bool):
        raise AssetStoreError(
            f"asset registry {key} must be an integer"
        )

    return value


def _require_non_blank(
    name: str,
    value: str,
) -> None:
    if not value or not value.strip():
        raise AssetStoreError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise AssetStoreError(
            f"{name} must not contain surrounding whitespace"
        )
