"""P0 skill identity/provenance coverage tests."""

import hashlib
from pathlib import Path

from services.p0_skill_catalog import (
    P0_FIRST_PARTY_SKILLS,
    provision_engineering_primary_skills,
    provision_non_engineering_p0_skills,
    validate_p0_skill_catalog,
)

ROOT = Path(__file__).resolve().parents[1]


class _CaptureExecutor:
    def __init__(self) -> None:
        self.skills: dict[str, tuple[bytes, frozenset[str]]] = {}

    def provision_skill(
        self, skill_id: str, content: bytes, authorities: frozenset[str]
    ) -> str:
        assert skill_id not in self.skills
        self.skills[skill_id] = (content, authorities)
        return hashlib.sha256(content).hexdigest()


def test_core_security_catalog_covers_exact_11_primary_bindings() -> None:
    validate_p0_skill_catalog()
    assert len(P0_FIRST_PARTY_SKILLS) == 11
    assert len({item.owner_agent_id for item in P0_FIRST_PARTY_SKILLS}) == 11
    assert all(item.instructions.strip() for item in P0_FIRST_PARTY_SKILLS)


def test_non_engineering_p0_skills_provision_as_immutable_text() -> None:
    executor = _CaptureExecutor()
    digests = provision_non_engineering_p0_skills(executor)  # type: ignore[arg-type]
    assert len(digests) == 11
    assert set(digests) == set(executor.skills)
    assert all(len(digest) == 64 for digest in digests.values())
    assert all(len(authorities) == 1 for _, authorities in executor.skills.values())


def test_engineering_primary_skills_are_loaded_from_existing_sf7_packages() -> None:
    executor = _CaptureExecutor()
    digests = provision_engineering_primary_skills(
        executor, ROOT  # type: ignore[arg-type]
    )
    assert len(digests) == 10
    assert set(digests) == set(executor.skills)
    assert "sf-core-engineering" in digests
    assert b"single canonical Core" in executor.skills["sf-core-engineering"][0]
    assert all(content.startswith(b"# sf-") for content, _ in executor.skills.values())
