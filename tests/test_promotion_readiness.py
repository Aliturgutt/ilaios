"""Promotion eligibility drill tests for PLATFORM.P20."""

import pytest

from packages.contracts.ilaios_contracts import ReleaseState
from services.readiness import REQUIRED_DRILLS, evaluate_drills


def test_all_drills_create_evidence_but_do_not_promote_release() -> None:
    result = evaluate_drills(dict.fromkeys(REQUIRED_DRILLS, True))
    assert result.eligible is True
    assert result.release_state is ReleaseState.NOT_DEPLOYED
    assert set(result.completed_drills) == REQUIRED_DRILLS
    assert len(result.evidence_hash) == 64


def test_missing_or_failed_drill_blocks_eligibility() -> None:
    results = dict.fromkeys(REQUIRED_DRILLS, True)
    results["rollback"] = False
    with pytest.raises(ValueError, match="rollback"):
        evaluate_drills(results)
    del results["load"]
    with pytest.raises(ValueError, match="load"):
        evaluate_drills(results)
