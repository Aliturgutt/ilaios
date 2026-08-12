from pathlib import Path

from services.research_data_factory import ResearchDataFactory
from services.research_data_store import SQLiteResearchDataStore


def test_research_records_persist_across_restart(tmp_path: Path) -> None:
    factory = ResearchDataFactory()
    source_a = factory.register_source(
        "source-a",
        locator="file:///a.json",
        content=b'{"value": 1}',
        trusted=True,
        metadata={"adapter": "json"},
    )
    source_b = factory.register_source(
        "source-b",
        locator="file:///b.json",
        content=b'{"value": 1}',
        trusted=True,
        metadata={"adapter": "json"},
    )
    claim = factory.propose_claim(
        "claim-1", statement="value is one", source_ids=("source-a", "source-b")
    )
    claim = factory.verify_claim("claim-1")
    analysis = factory.analyze_numeric("analysis-1", (1.0, 2.0, 3.0))
    database = tmp_path / "research.sqlite3"

    with SQLiteResearchDataStore(database) as store:
        store.save_source(source_a)
        store.save_source(source_b)
        store.save_claim(claim)
        store.save_analysis(analysis)

    with SQLiteResearchDataStore(database) as reopened:
        loaded_source = reopened.load_source("source-a")
        loaded_claim = reopened.load_claim("claim-1")
        loaded_analysis = reopened.load_analysis("analysis-1")

        assert loaded_source == source_a
        assert loaded_claim == claim
        assert loaded_claim is not None and loaded_claim.verified is True
        assert loaded_analysis == analysis
        assert reopened.load_source("missing") is None
