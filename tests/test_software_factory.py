"""Isolation and controlled self-change tests for PLATFORM.P18."""

import pytest

from services.software_factory import IsolatedSoftwareFactory, SoftwareFactoryError


def test_factory_emits_reviewable_bounded_proposal_only() -> None:
    factory = IsolatedSoftwareFactory(frozenset({"src", "tests"}))
    proposal = factory.propose("src/feature.py", b"value = 1\n")
    assert proposal.requires_human_approval is True
    assert proposal.production_applied is False
    assert proposal.proposal_id.startswith("change-")


def test_factory_blocks_escape_and_direct_production_mutation() -> None:
    factory = IsolatedSoftwareFactory(frozenset({"src"}))
    with pytest.raises(SoftwareFactoryError, match="escapes"):
        factory.propose("../secrets", b"x")
    with pytest.raises(SoftwareFactoryError, match="allowlist"):
        factory.propose("infra/prod.yaml", b"x")
    proposal = factory.propose("src/safe.py", b"x")
    with pytest.raises(SoftwareFactoryError, match="forbidden"):
        factory.apply_to_production(proposal)
