from dataclasses import replace
from datetime import datetime, timedelta, timezone
import pytest
from services.desktop_agent_eligibility import EligibilityEvidence, evaluate_eligibility

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)
BASE = EligibilityEvidence('agent-a', 'tenant-a', 'tenant-a', True, True, True,
                           'verified', 'agent-a', 'idle', NOW, 'agent-a', True)

def test_complete_fresh_trusted_evidence():
    assert evaluate_eligibility(BASE, now=NOW).eligible

@pytest.mark.parametrize('changes', [
    {'agent_id': ''}, {'canonical_registered': False},
    {'persisted_registered': False}, {'canonical_authority_matches': False},
    {'session_tenant': ''}, {'owner_tenant': None}, {'owner_tenant': 'tenant-b'},
    {'readiness': None}, {'readiness': 'executable'},
    {'live_agent_id': None}, {'live_agent_id': 'agent-b'},
    {'live_status': None}, {'live_status': 'offline'}, {'live_status': 'busy'},
    {'live_observed_at': None},
    {'live_observed_at': NOW - timedelta(seconds=31)},
    {'live_observed_at': NOW + timedelta(seconds=1)},
    {'live_observed_at': datetime(2026, 9, 28)},
    {'adapter_agent_id': None}, {'adapter_agent_id': 'agent-b'},
    {'adapter_verified': False},
])
def test_missing_conflicting_or_stale_evidence_fails_closed(changes):
    assert not evaluate_eligibility(replace(BASE, **changes), now=NOW).eligible

def test_multiple_failures_reported_without_side_effects():
    result = evaluate_eligibility(replace(BASE, owner_tenant=None, live_status='offline',
                                          adapter_verified=False), now=NOW)
    assert len(result.reasons) == 3
    assert not result.eligible
