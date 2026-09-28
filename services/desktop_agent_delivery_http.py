"""Loopback-only agent delivery endpoint; never executes work on acknowledgement."""
import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AgentDeliveryHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, delivery):
        if address[0] not in ('127.0.0.1', 'localhost'):
            raise ValueError('agent delivery must be loopback-only')
        super().__init__(address, AgentDeliveryHandler)
        self.delivery = delivery


class AgentDeliveryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ('/v1/agents/delivery/claim', '/v1/agents/delivery/ack'):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            size = int(self.headers.get('Content-Length', '-1'))
            if not 0 < size <= 2048:
                raise ValueError('invalid payload size')
            body = json.loads(self.rfile.read(size))
            keys = {'request_id', 'agent_id'} if self.path.endswith('/claim') else {
                'request_id', 'agent_id', 'lease'}
            if not isinstance(body, dict) or set(body) != keys or any(
                    not isinstance(v, str) or not v for v in body.values()):
                raise ValueError('invalid payload')
            auth = self.headers.get('Authorization', '')
            secret = auth[7:] if auth.startswith('Bearer ') else ''
            now = datetime.now(timezone.utc)
            if self.path.endswith('/claim'):
                lease = self.server.delivery.claim(**body, secret=secret, now=now)
                payload = json.dumps({'lease': lease}).encode()
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.server.delivery.acknowledge(**body, secret=secret, now=now)
                self.send_response(HTTPStatus.NO_CONTENT)
                self.send_header('Content-Length', '0')
                self.end_headers()
        except (ValueError, UnicodeError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST)
        except PermissionError:
            self.send_error(HTTPStatus.FORBIDDEN)

    def log_message(self, format, *args):
        pass
