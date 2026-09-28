import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from services.desktop_agent_eligibility_adapter import desktop_agent_eligibility

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)
LIVE = {'agent_id': 'agent-a', 'status': 'idle', 'observed_at': NOW}
ADAPTER = {'agent_id': 'agent-a', 'verified': True}
ROW = {'agent_id': 'agent-a', 'registered': True,
       'authority_matches_canonical': True, 'readiness': 'verified'}

def database(path: Path):
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE web_app_agents (tenant_id TEXT, agent_id TEXT, deleted_at TEXT)')
        conn.execute('INSERT INTO web_app_agents VALUES (?, ?, NULL)', ('tenant-a', 'agent-a'))

def check(db, tenant='tenant-a', live=LIVE, adapter=ADAPTER):
    with patch('services.desktop_agent_eligibility_adapter.canonical_agent_state',
               return_value={'agents': [ROW]}):
        return desktop_agent_eligibility(runtime=object(), db=db, tenant=tenant,
               agent='agent-a', live=live, adapter=adapter, now=NOW)

def test_trusted_sources_complete(tmp_path):
    db = tmp_path / 'runtime.sqlite3'; database(db)
    assert check(db).eligible

def test_missing_live_state_denied(tmp_path):
    db = tmp_path / 'runtime.sqlite3'; database(db)
    result = check(db, live=None)
    assert not result.eligible and 'fresh_live_state_unverified' in result.reasons

def test_missing_or_cross_tenant_ownership_denied(tmp_path):
    db = tmp_path / 'runtime.sqlite3'; database(db)
    for tenant in ('tenant-b', ''):
        result = check(db, tenant=tenant)
        assert not result.eligible and 'tenant_ownership_unverified' in result.reasons
    assert not check(tmp_path / 'missing.sqlite3').eligible

def test_missing_verified_adapter_denied(tmp_path):
    db = tmp_path / 'runtime.sqlite3'; database(db)
    assert not check(db, adapter=None).eligible

def test_missing_canonical_registration_denied(tmp_path):
    db = tmp_path / 'runtime.sqlite3'; database(db)
    with patch('services.desktop_agent_eligibility_adapter.canonical_agent_state',
               return_value={'agents': []}):
        result = desktop_agent_eligibility(runtime=object(), db=db,
             tenant='tenant-a', agent='agent-a', live=LIVE, adapter=ADAPTER, now=NOW)
    assert not result.eligible
