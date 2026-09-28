"""Real loopback HTTP tests for authenticated, short-lived agent heartbeat."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import Thread
import pytest
import requests
from services.desktop_agent_heartbeat import AgentHeartbeatHTTPServer, AgentHeartbeatStore
from services.desktop_agent_trust_evidence import validate_live


@contextmanager
def server():
    store = AgentHeartbeatStore({'agent-a': 'server-provisioned-a', 'agent-b': 'server-provisioned-b'})
    http = AgentHeartbeatHTTPServer(('127.0.0.1', 0), store)
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{http.server_address[1]}/v1/agents/heartbeat', store
    finally:
        http.shutdown()
        thread.join(timeout=3)
        http.server_close()


def post(url, *, agent='agent-a', token='server-provisioned-a', status='idle', body=None):
    return requests.post(url, json=body if body is not None else {'agent_id': agent, 'status': status},
        headers={'Authorization': f'Bearer {token}'}, timeout=3)


def test_authenticated_live_http_heartbeat_is_short_lived_and_agent_bound():
    with server() as (url, store):
        assert post(url).status_code == 204
        now = datetime.now(timezone.utc)
        live = store.live(agent_id='agent-a', now=now)
        assert validate_live(live, agent_id='agent-a', now=now,
            trusted_producers=frozenset({store.producer_id}))
        assert store.live(agent_id='agent-b', now=now) is None
        assert store.live(agent_id='agent-a', now=now + timedelta(seconds=31)) is None
        assert store.adapter(agent_id='agent-a', adapter_id='adapter-a', now=now) is None


@pytest.mark.parametrize('agent,token,status', [
    ('agent-a', 'wrong', 'idle'), ('agent-b', 'server-provisioned-a', 'idle'),
    ('unknown', 'server-provisioned-a', 'idle'), ('agent-a', '', 'idle'),
    ('agent-a', 'server-provisioned-a', 'forged'),
])
def test_invalid_http_heartbeat_cannot_produce_live_evidence(agent, token, status):
    with server() as (url, store):
        assert post(url, agent=agent, token=token, status=status).status_code == 401
        assert store.live(agent_id=agent, now=datetime.now(timezone.utc)) is None


@pytest.mark.parametrize('body', [
    {'agent_id': 'agent-a', 'status': 'idle', 'authenticated': True},
    {'agent_id': 'agent-a', 'status': 'idle', 'adapter_verified': True},
    {'agent_id': 'agent-a'},
])
def test_http_rejects_forged_evidence_and_incomplete_body(body):
    with server() as (url, store):
        assert post(url, body=body).status_code == 400
        assert store.live(agent_id='agent-a', now=datetime.now(timezone.utc)) is None
