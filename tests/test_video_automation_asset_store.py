"""Tests for canonical M13 Asset Store & Provenance."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.asset_store import (
    AssetStoreError,
    PersistentAssetStore,
)
from src.video_automation.generated_asset_retrieval import (
    RetrievedGenerationAsset,
)
from src.video_automation.models import MediaType


def _retrieved(
    directory: Path,
    *,
    asset_id: str = "asset-1",
    body: bytes = b"retrieved-video",
) -> RetrievedGenerationAsset:
    path = directory / f"{asset_id}.mp4"
    path.write_bytes(body)

    return RetrievedGenerationAsset(
        asset_id=asset_id,
        dispatch_id="dispatch-1",
        provider_job_id="provider-job-1",
        provider_id="test-provider",
        batch_number=1,
        output_index=1,
        local_path=str(path),
        sha256_hex=sha256(body).hexdigest(),
        byte_length=len(body),
        content_type="video/mp4",
        metadata={
            "source_asset_id": "fixture://generated-video-1",
        },
    )


def test_registers_retrieved_asset_as_existing_media_asset_model() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        store = PersistentAssetStore(
            directory / "registry.json"
        )
        retrieved = _retrieved(directory)

        asset = store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=retrieved,
        )

        assert asset.asset_id == "asset-1"
        assert asset.job_id == "job-1"
        assert asset.media_type is MediaType.VIDEO
        assert asset.file_path == str(
            Path(retrieved.local_path).resolve()
        )
        assert asset.checksum_sha256 == retrieved.sha256_hex
        assert asset.provider_name == "test-provider"
        assert asset.source_reference == "fixture://generated-video-1"
        assert asset.validated is False


def test_provenance_is_retained() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        store = PersistentAssetStore(
            directory / "registry.json"
        )

        asset = store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=_retrieved(directory),
        )

        record = store.get_record(asset.asset_id)

        assert record.dispatch_id == "dispatch-1"
        assert record.provider_job_id == "provider-job-1"
        assert record.batch_number == 1
        assert record.output_index == 1
        assert record.asset.provider_name == "test-provider"


def test_registration_persists_across_store_restart() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        registry = directory / "registry.json"

        first_store = PersistentAssetStore(registry)

        first_asset = first_store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=_retrieved(directory),
        )

        second_store = PersistentAssetStore(registry)
        second_asset = second_store.get("asset-1")

        assert second_asset == first_asset
        assert second_store.get_record(
            "asset-1"
        ).provider_job_id == "provider-job-1"


def test_registry_is_deterministic_and_sorted() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        registry = directory / "registry.json"
        store = PersistentAssetStore(registry)

        store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=_retrieved(
                directory,
                asset_id="asset-z",
                body=b"z",
            ),
        )

        store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=_retrieved(
                directory,
                asset_id="asset-a",
                body=b"a",
            ),
        )

        assert store.list_asset_ids() == (
            "asset-a",
            "asset-z",
        )

        payload = json.loads(
            registry.read_text(encoding="utf-8")
        )

        assert [
            item["asset_id"]
            for item in payload["assets"]
        ] == [
            "asset-a",
            "asset-z",
        ]


def test_same_registration_is_idempotent() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        store = PersistentAssetStore(
            directory / "registry.json"
        )
        retrieved = _retrieved(directory)

        first = store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=retrieved,
        )

        second = store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=retrieved,
        )

        assert second == first
        assert store.list_asset_ids() == ("asset-1",)


def test_conflicting_duplicate_asset_id_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        store = PersistentAssetStore(
            directory / "registry.json"
        )

        first = _retrieved(
            directory,
            asset_id="asset-1",
            body=b"first",
        )

        store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=first,
        )

        second_path = directory / "second.mp4"
        second_path.write_bytes(b"second")

        conflicting = RetrievedGenerationAsset(
            asset_id="asset-1",
            dispatch_id="dispatch-2",
            provider_job_id="provider-job-2",
            provider_id="other-provider",
            batch_number=2,
            output_index=1,
            local_path=str(second_path),
            sha256_hex=sha256(b"second").hexdigest(),
            byte_length=len(b"second"),
            content_type="video/mp4",
            metadata={
                "source_asset_id": "fixture://other",
            },
        )

        with pytest.raises(
            AssetStoreError,
            match="different evidence",
        ):
            store.register_retrieved_asset(
                job_id="job-1",
                media_type=MediaType.VIDEO,
                retrieved=conflicting,
            )


def test_registration_rejects_missing_local_file() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        retrieved = _retrieved(directory)

        Path(retrieved.local_path).unlink()

        store = PersistentAssetStore(
            directory / "registry.json"
        )

        with pytest.raises(
            AssetStoreError,
            match="does not exist",
        ):
            store.register_retrieved_asset(
                job_id="job-1",
                media_type=MediaType.VIDEO,
                retrieved=retrieved,
            )


def test_registration_rejects_checksum_mismatch() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        retrieved = _retrieved(directory)

        Path(retrieved.local_path).write_bytes(
            b"tampered"
        )

        store = PersistentAssetStore(
            directory / "registry.json"
        )

        with pytest.raises(
            AssetStoreError,
            match="checksum",
        ):
            store.register_retrieved_asset(
                job_id="job-1",
                media_type=MediaType.VIDEO,
                retrieved=retrieved,
            )


def test_registration_rejects_byte_length_mismatch() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        path = directory / "asset.mp4"
        body = b"body"
        path.write_bytes(body)

        retrieved = RetrievedGenerationAsset(
            asset_id="asset-1",
            dispatch_id="dispatch-1",
            provider_job_id="provider-job-1",
            provider_id="provider-1",
            batch_number=1,
            output_index=1,
            local_path=str(path),
            sha256_hex=sha256(body).hexdigest(),
            byte_length=len(body) + 1,
            content_type="video/mp4",
            metadata={},
        )

        store = PersistentAssetStore(
            directory / "registry.json"
        )

        with pytest.raises(
            AssetStoreError,
            match="byte_length",
        ):
            store.register_retrieved_asset(
                job_id="job-1",
                media_type=MediaType.VIDEO,
                retrieved=retrieved,
            )


def test_require_registered_path_revalidates_checksum() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        store = PersistentAssetStore(
            directory / "registry.json"
        )

        asset = store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=_retrieved(directory),
        )

        assert (
            store.require_registered_path(asset.asset_id)
            == Path(asset.file_path)
        )

        Path(asset.file_path).write_bytes(b"tampered")

        with pytest.raises(
            AssetStoreError,
            match="checksum changed",
        ):
            store.require_registered_path(asset.asset_id)


def test_validation_state_is_persistent() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        registry = directory / "registry.json"
        store = PersistentAssetStore(registry)

        store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=_retrieved(directory),
        )

        validated = store.set_validation_state(
            "asset-1",
            validated=True,
        )

        assert validated.validated is True

        reloaded = PersistentAssetStore(registry)

        assert reloaded.get("asset-1").validated is True


def test_unknown_asset_cannot_produce_uncontrolled_path() -> None:
    with TemporaryDirectory() as directory_name:
        store = PersistentAssetStore(
            Path(directory_name) / "registry.json"
        )

        with pytest.raises(
            AssetStoreError,
            match="not registered",
        ):
            store.require_registered_path(
                "unknown-asset"
            )


def test_corrupt_registry_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        registry = Path(directory_name) / "registry.json"
        registry.write_text(
            "{not-json",
            encoding="utf-8",
        )

        with pytest.raises(
            AssetStoreError,
            match="valid JSON",
        ):
            PersistentAssetStore(registry)


def test_unsupported_registry_schema_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        registry = Path(directory_name) / "registry.json"
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 99,
                    "assets": [],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(
            AssetStoreError,
            match="schema_version",
        ):
            PersistentAssetStore(registry)


def test_provenance_map_is_immutable() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        store = PersistentAssetStore(
            directory / "registry.json"
        )

        store.register_retrieved_asset(
            job_id="job-1",
            media_type=MediaType.VIDEO,
            retrieved=_retrieved(directory),
        )

        provenance = store.provenance_map()

        with pytest.raises(TypeError):
            provenance["other"] = provenance["asset-1"]  # type: ignore[index]
