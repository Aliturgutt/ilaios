import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from services.desktop_agent_eligibility_adapter import desktop_agent_eligibility
from services.desktop_agent_trust_evidence import LiveEvidence, AgentAdapterEvidence
NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)
LIVE = LiveEvidence('agent-a', 'trusted-server', NOW, NOW + timedelta(seconds=20), 'idle', True)
ADAPTER = AgentAdapterEvidence('agent-a', 'adapter-a', 'trusted-server', NOW,
                                NOW + timedelta(minutes=4), True, True)
ROW = {'agent_id': 'agent-a', 'registered': True,
       'authority_matches_canonical': True, 'readiness': 'verified'}

def check(tmp_path, *, live=LIVE, adapter=ADAPTER, trusted=frozenset({'trusted-server'}), tenant='tenant-a'):
    db = tmp_path / 'runtime.sqlite3'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS web_app_agents (tenant_id TEXT, agent_id TEXT, deleted_at TEXT)')
        conn.execute('DELETE FROM web_app_agents')
        conn.execute('INSERT INTO web_app_agents VALUES (?, ?, NULL)', ('tenant-a', 'agent-a'))
    with patch('services.desktop_agent_eligibility_adapter.canonical_agent_state', return_value={'agents': [ROW]}):
        return desktop_agent_eligibility(runtime=object(), db=db, tenant=tenant,
            agent='agent-a', live=live, adapter=adapter, now=NOW,
            trusted_producers=trusted, required_adapter_id='adapter-a')

def test_trusted_evidence_can_pass_preflight(tmp_path):
    assert check(tmp_path).eligible

def test_no_real_producers_means_denial(tmp_path):
    result = check(tmp_path, trusted=frozenset())
    assert not result.eligible
    assert 'fresh_live_state_unverified' in result.reasons
    assert 'agent_bound_adapter_unverified' in result.reasons

def test_missing_live_or_adapter_denied(tmp_path):
    assert not check(tmp_path, live=None).eligible
    assert not check(tmp_path, adapter=None).eligible

def test_wrong_agent_stale_and_untrusted_evidence_denied(tmp_path):
    assert not check(tmp_path, live=replace(LIVE, agent_id='agent-b')).eligible
    assert not check(tmp_path, live=replace(LIVE, observed_at=NOW-timedelta(seconds=31))).eligible
    assert not check(tmp_path, adapter=replace(ADAPTER, agent_id='agent-b')).eligible
    assert not check(tmp_path, adapter=replace(ADAPTER, producer_id='unknown')).eligible

def test_missing_tenant_ownership_denied_even_with_evidence(tmp_path):
    result = check(tmp_path, tenant='tenant-b')
    assert not result.eligible and 'tenant_ownership_unverified' in result.reasons
