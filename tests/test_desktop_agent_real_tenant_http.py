"""Tenant boundary with real SQLite ownership, real heartbeat HTTP and coordinator.

Verified readiness is simulated only in the positive path; separate real-runtime
case proves missing readiness evidence cannot be bypassed.
"""
import sqlite3
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch
import requests
from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.desktop_agent_adapter_verifier import VerifiedAgentAdapterStore
from services.desktop_agent_coordinator_verifier import CoordinatorAdapterVerifier
from services.desktop_agent_preflight import AgentPreflight
from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.runtime import GovernedRuntime
from tests.test_execution_coordinator import _coordinator
from services.execution_coordinator import classify_execution_plan

OBJECTIVE = 'Create a video about our product'
CAPABILITY = classify_execution_plan(OBJECTIVE).capability_ids[0]
AGENT = next(r for r in CANONICAL_AGENT_REGISTRY if r.backing_capability == 'video-factory')


def test_real_sqlite_live_http_cross_tenant_isolation(tmp_path):
    runtime_db = tmp_path / 'runtime.sqlite3'
    from services.control_plane.migrations import migrate_database
    migrate_database(runtime_db)
    runtime = GovernedRuntime(runtime_db)
    runtime.register_agent(AGENT.manifest.agent_id, AGENT.manifest.capabilities)
    with sqlite3.connect(runtime_db) as conn:
        conn.execute('INSERT INTO web_app_agents (tenant_id, project_id, agent_id, owner_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', ('tenant-a', 'project-a', AGENT.manifest.agent_id, 'user-a', '2026-09-28', '2026-09-28'))
    coordinator, *_ = _coordinator(tmp_path)
    identity = Mock()
    identity.validate_session.side_effect = lambda sid: SimpleNamespace(
        principal_id='user-a' if sid == 'a' else 'user-b',
        tenant_id='tenant-a' if sid == 'a' else 'tenant-b')
    video = next(row for row in coordinator.adapter_matrix() if row['adapter_id'] == 'video.product-runtime.v1')
    assert video['capability_id'] == CAPABILITY
    verifier = CoordinatorAdapterVerifier(coordinator, {AGENT.manifest.agent_id: CAPABILITY})
    adapters = VerifiedAgentAdapterStore({AGENT.manifest.agent_id: video['adapter_id']}, verifier)
    # The heartbeat test uses independently provisioned canonical agent credentials.
    # independently provisioned canonical agent HTTP server here.
    from services.desktop_agent_heartbeat import AgentHeartbeatHTTPServer, AgentHeartbeatStore
    live = AgentHeartbeatStore({AGENT.manifest.agent_id: 'canonical-agent-secret'})
    live_http = AgentHeartbeatHTTPServer(('127.0.0.1', 0), live)
    live_thread = Thread(target=live_http.serve_forever, daemon=True)
    live_thread.start()
    try:
        live_url = f'http://127.0.0.1:{live_http.server_address[1]}/v1/agents/heartbeat'
        beat = requests.post(live_url, json={'agent_id': AGENT.manifest.agent_id, 'status': 'idle'},
            headers={'Authorization': 'Bearer canonical-agent-secret'}, timeout=3)
        assert beat.status_code == 204
        preflight = AgentPreflight(live, adapters)
        config = {'bindings': {AGENT.manifest.agent_id: (video['adapter_id'], CAPABILITY)},
            'preflight': preflight, 'runtime': runtime, 'db': runtime_db}
        http = DesktopIdentityHTTPServer(('127.0.0.1', 0), bearer_token='token',
            identity=identity, coordinator=coordinator, agent_assignment=config)
        thread = Thread(target=http.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{http.server_address[1]}/v1/desktop/agents/assignments'
        body = {'agent_id': AGENT.manifest.agent_id, 'objective': OBJECTIVE, 'explicit_confirmation': True}
        try:
            denied = requests.post(url, json=body, headers={
                'Authorization': 'Bearer token', 'X-ILAIOS-Session': 'b'}, timeout=3)
            assert denied.status_code == 403, denied.text
            with sqlite3.connect(coordinator._database_path) as conn:
                assert conn.execute('SELECT COUNT(*) FROM execution_requests').fetchone()[0] == 0
            # No verified readiness proof exists in this real runtime:
            # even the owning tenant must be rejected, not silently promoted.
            owner = requests.post(url, json=body, headers={
                'Authorization': 'Bearer token', 'X-ILAIOS-Session': 'a'}, timeout=3)
            assert owner.status_code == 403, owner.text
            with sqlite3.connect(coordinator._database_path) as conn:
                assert conn.execute('SELECT COUNT(*) FROM execution_requests').fetchone()[0] == 0
            # Isolate the tenant predicate with a controlled verified-readiness
            # projection; the real ownership DB, HTTP and coordinator remain in use.
            row = {'agent_id': AGENT.manifest.agent_id, 'registered': True,
                'authority_matches_canonical': True, 'readiness': 'verified'}
            with patch('services.desktop_agent_eligibility_adapter.canonical_agent_state',
                       return_value={'agents': [row]}):
                cross = requests.post(url, json=body, headers={
                    'Authorization': 'Bearer token', 'X-ILAIOS-Session': 'b'}, timeout=3)
                assert cross.status_code == 403, cross.text
                with sqlite3.connect(coordinator._database_path) as conn:
                    assert conn.execute('SELECT COUNT(*) FROM execution_requests').fetchone()[0] == 0
                own = requests.post(url, json=body, headers={
                    'Authorization': 'Bearer token', 'X-ILAIOS-Session': 'a'}, timeout=3)
                assert own.status_code in (201, 409), own.text
                with sqlite3.connect(coordinator._database_path) as conn:
                    rows = conn.execute('SELECT principal_id, tenant_id FROM execution_requests').fetchall()
                assert rows and all(row == ('user-a', 'tenant-a') for row in rows)
        finally:
            http.shutdown(); thread.join(timeout=3); http.server_close()
    finally:
        live_http.shutdown(); live_thread.join(timeout=3); live_http.server_close()
