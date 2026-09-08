"""Tests for bounded Research/Data Factory provenance and verification gates."""

import pytest

from services.research_data_factory import ResearchDataError, ResearchDataFactory


def _factory_with_sources() -> ResearchDataFactory:
    factory = ResearchDataFactory()
    factory.register_source(
        "source-a",
        locator="fixture://source-a",
        content=b"independent evidence A",
        trusted=True,
        metadata={"publisher": "fixture-a"},
    )
    factory.register_source(
        "source-b",
        locator="fixture://source-b",
        content=b"independent evidence B",
        trusted=True,
        metadata={"publisher": "fixture-b"},
    )
    return factory


def test_verified_claim_projects_fact_and_provenance() -> None:
    factory = _factory_with_sources()
    claim = factory.propose_claim(
        "claim-1",
        statement="The bounded fixture is supported by two independent sources.",
        source_ids=("source-a", "source-b"),
    )
    assert claim.verified is False

    verified = factory.verify_claim("claim-1")
    assert verified.verified is True
    assert verified.verification_mode == "TRUST_THRESHOLD"

    projection = factory.knowledge_projection("claim-1")
    assert projection["fact"]["node_type"] == "Fact"
    assert projection["fact"]["verified"] is True
    assert projection["fact"]["verification_mode"] == "TRUST_THRESHOLD"
    assert [item["node_type"] for item in projection["evidence"]] == [
        "Evidence",
        "Evidence",
    ]
    assert {item["edge_type"] for item in projection["edges"]} == {"derived_from"}
    assert all(len(item["content_sha256"]) == 64 for item in projection["evidence"])


def test_unverified_or_under_supported_claim_fails_closed() -> None:
    factory = ResearchDataFactory()
    factory.register_source(
        "source-only",
        locator="fixture://single",
        content=b"single source",
        trusted=True,
    )
    factory.propose_claim(
        "claim-single",
        statement="A single source must not become a verified fact by default.",
        source_ids=("source-only",),
    )

    with pytest.raises(ResearchDataError, match="sufficient trusted independent sources"):
        factory.verify_claim("claim-single")
    with pytest.raises(ResearchDataError, match="only verified claims"):
        factory.knowledge_projection("claim-single")


def test_untrusted_source_does_not_count_as_independent_support() -> None:
    factory = ResearchDataFactory()
    factory.register_source(
        "trusted",
        locator="fixture://trusted",
        content=b"trusted",
        trusted=True,
    )
    factory.register_source(
        "untrusted",
        locator="fixture://untrusted",
        content=b"untrusted",
        trusted=False,
    )
    factory.propose_claim(
        "claim-mixed",
        statement="Mixed trust is insufficient for the default verification threshold.",
        source_ids=("trusted", "untrusted"),
    )
    with pytest.raises(ResearchDataError, match="sufficient trusted independent sources"):
        factory.verify_claim("claim-mixed")


def test_factual_claim_requires_content_bound_fresh_independent_evidence() -> None:
    factory = ResearchDataFactory()
    factory.register_source(
        "source-a",
        locator="fixture://source-a",
        content=b"Revenue reached 10 billion in 2026 according to audited results.",
        trusted=True,
        metadata={"publisher": "publisher-a"},
    )
    factory.register_source(
        "source-b",
        locator="fixture://source-b",
        content=b"Audited 2026 results report revenue of 10 billion.",
        trusted=True,
        metadata={"publisher": "publisher-b"},
    )
    factory.propose_claim(
        "claim-factual",
        statement="Revenue reached 10 billion in 2026.",
        source_ids=("source-a", "source-b"),
    )
    factory.register_claim_evidence(
        "claim-factual",
        source_id="source-a",
        excerpt=b"Revenue reached 10 billion in 2026",
        stance="supports",
        validator_evidence_ref="evidence://validator/a",
        published_on="2026-08-01",
    )
    factory.register_claim_evidence(
        "claim-factual",
        source_id="source-b",
        excerpt=b"revenue of 10 billion",
        stance="SUPPORTS",
        validator_evidence_ref="evidence://validator/b",
        published_on="2026-08-02",
    )

    verified = factory.verify_factual_claim(
        "claim-factual",
        as_of="2026-09-08",
        max_source_age_days=90,
    )
    assert verified.verified is True
    assert verified.verification_mode == "CONTENT_BOUND_FACTUAL"

    projection = factory.knowledge_projection("claim-factual")
    assert projection["fact"]["verification_mode"] == "CONTENT_BOUND_FACTUAL"
    assert all(item["validator_evidence_ref"] for item in projection["evidence"])
    assert all(len(item["excerpt_sha256"]) == 64 for item in projection["evidence"])


def test_factual_claim_rejects_excerpt_not_present_in_source() -> None:
    factory = ResearchDataFactory()
    factory.register_source(
        "source-a",
        locator="fixture://source-a",
        content=b"actual source text",
        trusted=True,
        metadata={"publisher": "publisher-a"},
    )
    factory.propose_claim(
        "claim-a",
        statement="A factual statement.",
        source_ids=("source-a",),
    )
    with pytest.raises(ResearchDataError, match="not present in source content"):
        factory.register_claim_evidence(
            "claim-a",
            source_id="source-a",
            excerpt=b"invented excerpt",
            stance="SUPPORTS",
            validator_evidence_ref="evidence://validator/a",
            published_on="2026-09-01",
        )


def test_factual_claim_rejects_conflicting_stale_and_non_independent_evidence() -> None:
    factory = ResearchDataFactory()
    factory.register_source(
        "source-a",
        locator="fixture://source-a",
        content=b"support text",
        trusted=True,
        metadata={"publisher": "same-publisher"},
    )
    factory.register_source(
        "source-b",
        locator="fixture://source-b",
        content=b"contradiction text",
        trusted=True,
        metadata={"publisher": "publisher-b"},
    )
    factory.propose_claim(
        "claim-conflict",
        statement="A factual statement.",
        source_ids=("source-a", "source-b"),
    )
    factory.register_claim_evidence(
        "claim-conflict",
        source_id="source-a",
        excerpt=b"support text",
        stance="SUPPORTS",
        validator_evidence_ref="evidence://validator/a",
        published_on="2026-09-01",
    )
    factory.register_claim_evidence(
        "claim-conflict",
        source_id="source-b",
        excerpt=b"contradiction text",
        stance="CONTRADICTS",
        validator_evidence_ref="evidence://validator/b",
        published_on="2026-09-01",
    )
    with pytest.raises(ResearchDataError, match="contradictory trusted evidence"):
        factory.verify_factual_claim(
            "claim-conflict",
            as_of="2026-09-08",
            max_source_age_days=30,
        )

    stale = ResearchDataFactory()
    stale.register_source(
        "source-a",
        locator="fixture://source-a",
        content=b"support A",
        trusted=True,
        metadata={"publisher": "publisher-a"},
    )
    stale.register_source(
        "source-b",
        locator="fixture://source-b",
        content=b"support B",
        trusted=True,
        metadata={"publisher": "publisher-b"},
    )
    stale.propose_claim(
        "claim-stale",
        statement="A stale factual statement.",
        source_ids=("source-a", "source-b"),
    )
    for source_id, excerpt, ref in (
        ("source-a", b"support A", "evidence://validator/a"),
        ("source-b", b"support B", "evidence://validator/b"),
    ):
        stale.register_claim_evidence(
            "claim-stale",
            source_id=source_id,
            excerpt=excerpt,
            stance="SUPPORTS",
            validator_evidence_ref=ref,
            published_on="2025-01-01",
        )
    with pytest.raises(ResearchDataError, match="stale trusted evidence"):
        stale.verify_factual_claim(
            "claim-stale",
            as_of="2026-09-08",
            max_source_age_days=90,
        )

    same_publisher = ResearchDataFactory()
    for source_id, content in (("source-a", b"support A"), ("source-b", b"support B")):
        same_publisher.register_source(
            source_id,
            locator=f"fixture://{source_id}",
            content=content,
            trusted=True,
            metadata={"publisher": "same-publisher"},
        )
    same_publisher.propose_claim(
        "claim-same-publisher",
        statement="An insufficiently independent factual statement.",
        source_ids=("source-a", "source-b"),
    )
    for source_id, excerpt, ref in (
        ("source-a", b"support A", "evidence://validator/a"),
        ("source-b", b"support B", "evidence://validator/b"),
    ):
        same_publisher.register_claim_evidence(
            "claim-same-publisher",
            source_id=source_id,
            excerpt=excerpt,
            stance="SUPPORTS",
            validator_evidence_ref=ref,
            published_on="2026-09-01",
        )
    with pytest.raises(ResearchDataError, match="independent publishers"):
        same_publisher.verify_factual_claim(
            "claim-same-publisher",
            as_of="2026-09-08",
            max_source_age_days=30,
        )


def test_numeric_analysis_is_deterministic_and_bounded() -> None:
    first = ResearchDataFactory().analyze_numeric("analysis-1", (1.0, 2.0, 4.0))
    second = ResearchDataFactory().analyze_numeric("analysis-1", (1.0, 2.0, 4.0))

    assert first == second
    assert first.count == 3
    assert first.minimum == 1.0
    assert first.maximum == 4.0
    assert first.mean == pytest.approx(7.0 / 3.0)
    assert len(first.values_sha256) == 64


def test_unknown_source_duplicate_ids_and_nan_fail_closed() -> None:
    factory = _factory_with_sources()
    with pytest.raises(ResearchDataError, match="unknown sources"):
        factory.propose_claim(
            "claim-unknown",
            statement="Unknown evidence is invalid.",
            source_ids=("source-a", "missing"),
        )
    with pytest.raises(ResearchDataError, match="duplicates"):
        factory.propose_claim(
            "claim-duplicate",
            statement="Duplicate evidence is not independent evidence.",
            source_ids=("source-a", "source-a"),
        )
    with pytest.raises(ValueError):
        factory.analyze_numeric("analysis-nan", (1.0, float("nan")))
