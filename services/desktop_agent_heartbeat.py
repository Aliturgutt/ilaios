"""Isolated loopback authenticated agent heartbeat; never accepts client evidence.

This component is not wired into Desktop until agent credentials are provisioned.
"""
from __future__ import annotations
import hmac
import json
import threading
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from services.desktop_agent_trust_evidence import LiveEvidence


class AgentHeartbeatStore:
    def __init__(self, credentials: dict[str, str], *, producer_id: str = 'desktop-authenticated-heartbeat'):
        if not producer_id or not credentials or any(not k or not v for k, v in credentials.items()):
            raise ValueError('server-provisioned agent credentials required')
        self._credentials = dict(credentials)
        self.producer_id = producer_id
        self._lock = threading.RLock()
        self._observations: dict[str, LiveEvidence] = {}

    def record(self, agent_id: str, secret: str, status: str, *, now: datetime) -> bool:
        expected = self._credentials.get(agent_id)
        if (not expected or not secret or not hmac.compare_digest(expected, secret)
                or status not in ('idle', 'busy') or now.tzinfo is None):
            return False
        with self._lock:
            self._observations[agent_id] = LiveEvidence(agent_id, self.producer_id,
                now, now + timedelta(seconds=30), status, True)
        return True

    def live(self, *, agent_id: str, now: datetime) -> LiveEvidence | None:
        with self._lock:
            item = self._observations.get(agent_id)
        if item is None or now.tzinfo is None or not item.observed_at <= now <= item.expires_at:
            return None
        return item

    def adapter(self, *, agent_id: str, adapter_id: str, now: datetime):
        # Heartbeat is never evidence that an execution adapter was verified.
        return None


class AgentHeartbeatHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: AgentHeartbeatStore):
        if address[0] not in ('127.0.0.1', 'localhost'):
            raise ValueError('heartbeat HTTP must be loopback-only')
        super().__init__(address, AgentHeartbeatHandler)
        self.store = store


class AgentHeartbeatHandler(BaseHTTPRequestHandler):
    server: AgentHeartbeatHTTPServer

    def do_POST(self):
        if self.path != '/v1/agents/heartbeat':
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 < length <= 2048:
                raise ValueError('invalid body size')
            body = json.loads(self.rfile.read(length))
            if (not isinstance(body, dict) or set(body) != {'agent_id', 'status'}
                    or not all(isinstance(x, str) for x in body.values())):
                raise ValueError('invalid heartbeat fields')
        except (ValueError, UnicodeError):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        authorization = self.headers.get('Authorization', '')
        secret = authorization.removeprefix('Bearer ') if authorization.startswith('Bearer ') else ''
        if not self.server.store.record(body['agent_id'], secret, body['status'],
                                        now=datetime.now(timezone.utc)):
            self.send_error(HTTPStatus.UNAUTHORIZED)
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def log_message(self, format, *args):
        pass
