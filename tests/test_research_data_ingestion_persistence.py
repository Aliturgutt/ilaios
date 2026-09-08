"""Execution tests for governed Research/Data ingestion and durable persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from services.research_data_factory import (
    FetchedResearchSource,
    ResearchDataError,
    ResearchDataFactory,
)


class _Gateway:
    def __init__(self, payload: FetchedResearchSource) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def dispatch(
        self,
        tool_name: str,
        *args: Any,
        path: str | None = None,
        **kwargs: Any,
    ) -> Any:
        assert args == ()
        assert path is None
        self.calls.append((tool_name, kwargs))
        return self.payload


def test_external_json_ingestion_crosses_gateway_and_survives_restart(tmp_path: Path) -> None:
    database = tmp_path / "research.sqlite3"
    payload = FetchedResearchSource(
        final_locator="https://data.example.test/report.json",
        content=b'{"revenue": 10, "year": 2026}',
        retrieved_at="2026-09-08T20:00:00Z",
        media_type="application/json",
        provider_evidence_ref="evidence://egress/request-1",
        tenant_id="tenant-a",
    )
    gateway = _Gateway(payload)
    factory = ResearchDataFactory(
        database_path=database,
        tenant_id="tenant-a",
        tool_gateway=gateway,
    )

    record = factory.ingest_external_source(
        "source-json",
        locator="https://data.example.test/report.json",
        source_format="json",
        trusted=True,
        metadata={"publisher": "example-data"},
    )

    assert gateway.calls == [
        (
            "research.fetch_source",
            {
                "locator": "https://data.example.test/report.json",
                "tenant_id": "tenant-a",
                "max_bytes": 5_000_000,
            },
        )
    ]
    assert record.source_id == "source-json"
    assert record.provider_evidence_ref == "evidence://egress/request-1"
    assert len(record.content_sha256) == 64

    restored = ResearchDataFactory(database_path=database, tenant_id="tenant-a")
    assert restored.ingestion_record(record.ingestion_id) == record
    restored.propose_claim(
        "claim-restored",
        statement="Revenue is 10 in the fixture.",
        source_ids=("source-json",),
    )
    assert restored.verify_claim("claim-restored", min_independent_sources=1).verified is True


def test_csv_ingestion_is_validated_and_persisted(tmp_path: Path) -> None:
    database = tmp_path / "research.sqlite3"
    payload = FetchedResearchSource(
        final_locator="https://data.example.test/metrics.csv",
        content=b"year,revenue\n2026,10\n",
        retrieved_at="2026-09-08T20:05:00Z",
        media_type="text/csv",
        provider_evidence_ref="evidence://egress/request-2",
        tenant_id="tenant-a",
    )
    factory = ResearchDataFactory(
        database_path=database,
        tenant_id="tenant-a",
        tool_gateway=_Gateway(payload),
    )

    record = factory.ingest_external_source(
        "source-csv",
        locator="https://data.example.test/metrics.csv",
        source_format="csv",
        trusted=False,
    )

    restored = ResearchDataFactory(database_path=database, tenant_id="tenant-a")
    assert restored.ingestion_record(record.ingestion_id).source_format == "csv"


def test_durable_claim_evidence_analysis_and_verification_survive_restart(
    tmp_path: Path,
) -> None:
    database = tmp_path / "research.sqlite3"
    factory = ResearchDataFactory(database_path=database, tenant_id="tenant-a")
    factory.register_source(
        "source-a",
        locator="fixture://a",
        content=b"support A",
        trusted=True,
        metadata={"publisher": "publisher-a"},
    )
    factory.register_source(
        "source-b",
        locator="fixture://b",
        content=b"support B",
        trusted=True,
        metadata={"publisher": "publisher-b"},
    )
    factory.propose_claim(
        "claim-a",
        statement="A durable fact.",
        source_ids=("source-a", "source-b"),
    )
    factory.register_claim_evidence(
        "claim-a",
        source_id="source-a",
        excerpt=b"support A",
        stance="SUPPORTS",
        validator_evidence_ref="evidence://validator/a",
        published_on="2026-09-01",
    )
    factory.register_claim_evidence(
        "claim-a",
        source_id="source-b",
        excerpt=b"support B",
        stance="SUPPORTS",
        validator_evidence_ref="evidence://validator/b",
        published_on="2026-09-02",
    )
    factory.verify_factual_claim(
        "claim-a",
        as_of="2026-09-08",
        max_source_age_days=30,
    )
    analysis = factory.analyze_numeric("analysis-a", (1.0, 2.0, 3.0))

    restored = ResearchDataFactory(database_path=database, tenant_id="tenant-a")
    projection = restored.knowledge_projection("claim-a")
    assert projection["fact"]["verification_mode"] == "CONTENT_BOUND_FACTUAL"
    assert len(projection["evidence"]) == 2
    with pytest.raises(ResearchDataError, match="analysis_id already exists"):
        restored.analyze_numeric("analysis-a", (1.0, 2.0, 3.0))
    assert analysis.count == 3


def test_durable_storage_is_tenant_isolated(tmp_path: Path) -> None:
    database = tmp_path / "research.sqlite3"
    tenant_a = ResearchDataFactory(database_path=database, tenant_id="tenant-a")
    tenant_a.register_source(
        "shared-id",
        locator="fixture://tenant-a",
        content=b"tenant A",
        trusted=True,
    )

    tenant_b = ResearchDataFactory(database_path=database, tenant_id="tenant-b")
    tenant_b.register_source(
        "shared-id",
        locator="fixture://tenant-b",
        content=b"tenant B",
        trusted=True,
    )
    tenant_b.propose_claim(
        "claim-b",
        statement="Tenant B source.",
        source_ids=("shared-id",),
    )
    assert tenant_b.verify_claim("claim-b", min_independent_sources=1).verified is True

    restored_a = ResearchDataFactory(database_path=database, tenant_id="tenant-a")
    with pytest.raises(ResearchDataError, match="claim does not exist"):
        restored_a.knowledge_projection("claim-b")


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (
            FetchedResearchSource(
                final_locator="https://data.example.test/report.json",
                content=b"{not-json}",
                retrieved_at="2026-09-08T20:00:00Z",
                media_type="application/json",
                provider_evidence_ref="evidence://egress/request-3",
                tenant_id="tenant-a",
            ),
            "invalid",
        ),
        (
            FetchedResearchSource(
                final_locator="https://data.example.test/report.json",
                content=b'{"ok": true}',
                retrieved_at="2026-09-08T20:00:00Z",
                media_type="application/json",
                provider_evidence_ref="evidence://egress/request-4",
                tenant_id="tenant-b",
            ),
            "tenant boundary",
        ),
    ],
)
def test_external_ingestion_fails_closed_on_invalid_receipts(
    tmp_path: Path,
    payload: FetchedResearchSource,
    match: str,
) -> None:
    factory = ResearchDataFactory(
        database_path=tmp_path / "research.sqlite3",
        tenant_id="tenant-a",
        tool_gateway=_Gateway(payload),
    )
    with pytest.raises(ResearchDataError, match=match):
        factory.ingest_external_source(
            "source-a",
            locator="https://data.example.test/report.json",
            source_format="json",
            trusted=True,
        )


def test_external_ingestion_requires_tenant_gateway_https_and_supported_format(
    tmp_path: Path,
) -> None:
    with pytest.raises(ResearchDataError, match="requires tenant_id"):
        ResearchDataFactory(database_path=tmp_path / "missing-tenant.sqlite3")

    no_gateway = ResearchDataFactory(tenant_id="tenant-a")
    with pytest.raises(ResearchDataError, match="canonical ToolGateway"):
        no_gateway.ingest_external_source(
            "source-a",
            locator="https://data.example.test/report.json",
            source_format="json",
            trusted=True,
        )

    payload = FetchedResearchSource(
        final_locator="https://data.example.test/report.json",
        content=b'{"ok": true}',
        retrieved_at="2026-09-08T20:00:00Z",
        media_type="application/json",
        provider_evidence_ref="evidence://egress/request-5",
        tenant_id="tenant-a",
    )
    factory = ResearchDataFactory(tenant_id="tenant-a", tool_gateway=_Gateway(payload))
    with pytest.raises(ResearchDataError, match="must use HTTPS"):
        factory.ingest_external_source(
            "source-http",
            locator="http://data.example.test/report.json",
            source_format="json",
            trusted=True,
        )
    with pytest.raises(ResearchDataError, match="json or csv"):
        factory.ingest_external_source(
            "source-xml",
            locator="https://data.example.test/report.xml",
            source_format="xml",
            trusted=True,
        )
