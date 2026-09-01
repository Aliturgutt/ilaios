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

    projection = factory.knowledge_projection("claim-1")
    assert projection["fact"]["node_type"] == "Fact"
    assert projection["fact"]["verified"] is True
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
