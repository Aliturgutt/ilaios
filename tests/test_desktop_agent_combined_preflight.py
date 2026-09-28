"""Real heartbeat HTTP + independent server adapter + tenant-scoped preflight."""
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import pytest
from services.desktop_agent_adapter_verifier import VerifiedAgentAdapterStore
from services.desktop_agent_heartbeat import AgentHeartbeatStore
from services.desktop_agent_preflight import AgentPreflight
from tests.test_desktop_agent_heartbeat_http import server, post

ROW = {'agent_id': 'agent-a', 'registered': True,
       'authority_matches_canonical': True, 'readiness': 'verified'}


def test_real_http_and_server_verified_adapter_allow_tenant_scoped_preflight(tmp_path):
    db = tmp_path / 'agents.sqlite3'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE web_app_agents (tenant_id TEXT, agent_id TEXT, deleted_at TEXT)')
        conn.execute('INSERT INTO web_app_agents VALUES (?, ?, NULL)', ('tenant-a', 'agent-a'))
    verifier = Mock()
    verifier.verify.return_value = True
    with server() as (url, heartbeat):
        assert post(url).status_code == 204
        adapters = VerifiedAgentAdapterStore({'agent-a': 'adapter-a'}, verifier)
        gate = AgentPreflight(heartbeat, adapters)
        now = datetime.now(timezone.utc)
        with patch('services.desktop_agent_eligibility_adapter.canonical_agent_state',
                   return_value={'agents': [ROW]}):
            allowed = gate.check(runtime=object(), db=db, tenant='tenant-a',
                                 agent='agent-a', adapter_id='adapter-a', now=now)
            wrong_tenant = gate.check(runtime=object(), db=db, tenant='tenant-b',
                                      agent='agent-a', adapter_id='adapter-a', now=now)
            wrong_adapter = gate.check(runtime=object(), db=db, tenant='tenant-a',
                                       agent='agent-a', adapter_id='adapter-b', now=now)
            stale = gate.check(runtime=object(), db=db, tenant='tenant-a',
                               agent='agent-a', adapter_id='adapter-a',
                               now=now + timedelta(seconds=31))
        assert allowed.eligible, allowed.reasons
        assert not wrong_tenant.eligible and 'tenant_ownership_unverified' in wrong_tenant.reasons
        assert not wrong_adapter.eligible and 'agent_bound_adapter_unverified' in wrong_adapter.reasons
        assert not stale.eligible and 'fresh_live_state_unverified' in stale.reasons
        verifier.verify.assert_called_with(agent_id='agent-a', adapter_id='adapter-a')


@pytest.mark.parametrize('result', [False, None])
def test_server_verifier_denial_fails_closed(result):
    verifier = Mock()
    verifier.verify.return_value = result
    store = VerifiedAgentAdapterStore({'agent-a': 'adapter-a'}, verifier)
    assert store.adapter(agent_id='agent-a', adapter_id='adapter-a',
                         now=datetime.now(timezone.utc)) is None


def test_missing_verifier_or_wrong_binding_cannot_mint_adapter_evidence():
    now = datetime.now(timezone.utc)
    assert VerifiedAgentAdapterStore({'agent-a': 'adapter-a'}, None).adapter(
        agent_id='agent-a', adapter_id='adapter-a', now=now) is None
    verifier = Mock()
    store = VerifiedAgentAdapterStore({'agent-a': 'adapter-a'}, verifier)
    assert store.adapter(agent_id='agent-b', adapter_id='adapter-a', now=now) is None
    verifier.verify.assert_not_called()


def test_server_verifier_exception_fails_closed():
    verifier = Mock()
    verifier.verify.side_effect = RuntimeError('offline')
    store = VerifiedAgentAdapterStore({'agent-a': 'adapter-a'}, verifier)
    assert store.adapter(agent_id='agent-a', adapter_id='adapter-a',
                         now=datetime.now(timezone.utc)) is None
