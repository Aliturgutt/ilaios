"""Loopback-only agent delivery endpoint; never executes work on acknowledgement."""
import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AgentDeliveryHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, delivery, *, tls_context=None, agent_cert_fingerprints=None):
        import ssl
        if address[0] not in ('127.0.0.1', 'localhost') and tls_context is None:
            raise ValueError('remote agent delivery requires TLS')
        if tls_context is not None and (not isinstance(tls_context, ssl.SSLContext)
                                        or tls_context.verify_mode != ssl.CERT_REQUIRED):
            raise ValueError('agent TLS requires verified client certificates')
        if address[0] not in ('127.0.0.1', 'localhost') and not agent_cert_fingerprints:
            raise ValueError('remote agent certificates must be pinned to agent identities')
        if agent_cert_fingerprints is not None and (not isinstance(agent_cert_fingerprints, dict)
                or any(not isinstance(k, str) or not isinstance(v, str)
                       or len(v) != 64 or any(c not in '0123456789abcdef' for c in v)
                       for k, v in agent_cert_fingerprints.items())):
            raise ValueError('invalid agent certificate fingerprints')
        super().__init__(address, AgentDeliveryHandler)
        self.agent_cert_fingerprints = agent_cert_fingerprints
        if tls_context is not None:
            self.socket = tls_context.wrap_socket(self.socket, server_side=True)
        self.delivery = delivery


class AgentDeliveryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ('/v1/agents/delivery/claim', '/v1/agents/delivery/ack', '/v1/agents/delivery/result', '/v1/agents/delivery/artifact', '/v1/agents/delivery/status'):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            size = int(self.headers.get('Content-Length', '-1'))
            if not 0 < size <= (1400000 if self.path.endswith('/artifact') else 2048):
                raise ValueError('invalid payload size')
            body = json.loads(self.rfile.read(size))
            keys = ({'request_id', 'agent_id'} if self.path.endswith(('/claim', '/status')) else
                    {'request_id', 'agent_id', 'lease', 'artifact_b64', 'digest'} if self.path.endswith('/artifact') else
                    {'request_id', 'agent_id', 'lease', 'result'} if self.path.endswith('/result') else
                    {'request_id', 'agent_id', 'lease'})
            if not isinstance(body, dict) or set(body) != keys or any(
                    not isinstance(body[k], str) or not body[k] for k in keys - {'result'}):
                raise ValueError('invalid payload')
            pins = self.server.agent_cert_fingerprints
            if pins is not None:
                import hashlib
                import hmac
                certificate = self.connection.getpeercert(binary_form=True)
                expected = pins.get(body['agent_id'])
                if not certificate or not expected or not hmac.compare_digest(
                        hashlib.sha256(certificate).hexdigest(), expected):
                    raise PermissionError('agent certificate identity mismatch')
            auth = self.headers.get('Authorization', '')
            secret = auth[7:] if auth.startswith('Bearer ') else ''
            now = datetime.now(timezone.utc)
            if self.path.endswith('/status'):
                status = self.server.delivery.receipt_status(**body, secret=secret)
                payload = json.dumps(status).encode()
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            elif self.path.endswith('/claim'):
                lease = self.server.delivery.claim(**body, secret=secret, now=now)
                payload = json.dumps({'lease': lease}).encode()
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                if self.path.endswith('/artifact'):
                    from services.desktop_agent_result_receipt import AgentResultReceipt
                    from services.desktop_agent_verified_artifact import receive_verified
                    receive_verified(AgentResultReceipt(self.server.delivery), **body,
                                     secret=secret, now=now)
                    self.send_response(HTTPStatus.ACCEPTED)
                elif self.path.endswith('/result'):
                    from services.desktop_agent_result_receipt import AgentResultReceipt
                    AgentResultReceipt(self.server.delivery).submit(**body, secret=secret, now=now)
                    self.send_response(HTTPStatus.ACCEPTED)
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
