"""HTTP boundary for the short-lived provider reference relay.

Production must terminate TLS in front of this process. Upload/delete/access-evidence
operations require a server-held bearer token; provider GETs use only signed expiring
URLs. The handler never logs bearer tokens or signed query strings.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from services.reference_relay import ReferenceRelayError, SignedReferenceRelayStore
from services.reference_relay_access import ReferenceRelayAccessLedger

_MAX_UPLOAD_BODY_BYTES = 15 * 1024 * 1024


class ReferenceRelayHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        store: SignedReferenceRelayStore,
        access_ledger: ReferenceRelayAccessLedger,
        upload_token: str,
    ) -> None:
        if not upload_token or upload_token != upload_token.strip():
            raise ReferenceRelayError("reference relay upload token is invalid")
        super().__init__(server_address, ReferenceRelayRequestHandler)
        self.store = store
        self.access_ledger = access_ledger
        self.upload_token = upload_token


class ReferenceRelayRequestHandler(BaseHTTPRequestHandler):
    server: ReferenceRelayHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health/live":
            self._send_json(HTTPStatus.OK, {"status": "live"})
            return
        if parsed.path == "/health/ready":
            self.server.store.purge_expired()
            self._send_json(HTTPStatus.OK, {"status": "ready"})
            return
        access_prefix = "/v1/reference-relay-access/"
        if parsed.path.startswith(access_prefix):
            try:
                self._authenticate_upload()
                sha256_hex = parsed.path.removeprefix(access_prefix)
                evidence = self.server.access_ledger.evidence(sha256_hex)
            except PermissionError:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            except ReferenceRelayError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_reference"})
                return
            if evidence is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._send_json(
                HTTPStatus.OK,
                {
                    "sha256": evidence.sha256,
                    "fetch_count": evidence.fetch_count,
                    "first_fetched_at_epoch_s": evidence.first_fetched_at_epoch_s,
                    "last_fetched_at_epoch_s": evidence.last_fetched_at_epoch_s,
                },
            )
            return
        prefix = "/v1/reference-relay/"
        if not parsed.path.startswith(prefix):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        relay_id = parsed.path.removeprefix(prefix)
        query = parse_qs(parsed.query)
        try:
            expires = int(_single_query(query, "expires"))
            sha256_hex = _single_query(query, "sha256")
            signature = _single_query(query, "signature")
            content, mime_type = self.server.store.resolve(
                relay_id=relay_id,
                expires_at_epoch_s=expires,
                sha256_hex=sha256_hex,
                signature=signature,
            )
            self.server.access_ledger.record_fetch(sha256_hex)
        except (ReferenceRelayError, ValueError):
            # Do not reveal whether an id, digest, signature, or expiry was valid.
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/v1/reference-relay":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            self._authenticate_upload()
            body = self._read_json()
            content = _decode_base64(_required_string(body, "content_base64"))
            ticket = self.server.store.publish(
                content=content,
                mime_type=_required_string(body, "mime_type"),
                sha256_hex=_required_string(body, "sha256").lower(),
                tenant_id=_required_string(body, "tenant_id"),
                principal_id=_required_string(body, "principal_id"),
            )
        except PermissionError:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        except (ReferenceRelayError, ValueError, TypeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_reference"})
            return
        self._send_json(
            HTTPStatus.CREATED,
            {
                "relay_id": ticket.relay_id,
                "url": ticket.url,
                "sha256": ticket.sha256,
                "mime_type": ticket.mime_type,
                "expires_at_epoch_s": ticket.expires_at_epoch_s,
            },
        )

    def do_DELETE(self) -> None:
        prefix = "/v1/reference-relay/"
        path = urlparse(self.path).path
        if not path.startswith(prefix):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            self._authenticate_upload()
            self.server.store.release_id(path.removeprefix(prefix))
        except PermissionError:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        except ReferenceRelayError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_reference"})
            return
        self._send_json(HTTPStatus.OK, {"released": True})

    def log_message(self, message_format: str, *args: object) -> None:
        # BaseHTTPRequestHandler's default request log includes the full query
        # string, which contains the signed relay capability. Never emit it.
        print(
            json.dumps(
                {
                    "component": "reference_relay",
                    "client": self.client_address[0],
                    "event": "http_request",
                    "method": self.command,
                    "path": urlparse(self.path).path,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    def _authenticate_upload(self) -> None:
        value = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not value.startswith(prefix):
            raise PermissionError("missing relay bearer token")
        supplied = value.removeprefix(prefix)
        if not hmac.compare_digest(supplied, self.server.upload_token):
            raise PermissionError("invalid relay bearer token")

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("content length is required")
        length = int(raw_length)
        if length <= 0 or length > _MAX_UPLOAD_BODY_BYTES:
            raise ValueError("reference relay upload body size is invalid")
        raw = self.rfile.read(length)
        document = json.loads(raw.decode("utf-8"))
        if not isinstance(document, dict):
            raise TypeError("reference relay body must be an object")
        return document

    def _send_json(self, status: HTTPStatus, body: dict[str, object]) -> None:
        payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


def _required_string(body: dict[str, Any], name: str) -> str:
    value = body.get(name)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be trimmed text")
    return value


def _decode_base64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("reference relay content is not valid base64") from error


def _single_query(query: dict[str, list[str]], name: str) -> str:
    values = query.get(name, [])
    if len(values) != 1 or not values[0]:
        raise ValueError(f"missing {name}")
    return values[0]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ILAIOS provider reference relay")
    parser.add_argument("--host", default=os.environ.get("ILAIOS_REFERENCE_RELAY_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ILAIOS_REFERENCE_RELAY_PORT", "8091")),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("ILAIOS_REFERENCE_RELAY_DATA_DIR", "var/reference-relay")),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    public_base_url = os.environ.get("ILAIOS_REFERENCE_RELAY_PUBLIC_BASE_URL", "").strip()
    upload_token = os.environ.get("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", "").strip()
    signing_secret = os.environ.get("ILAIOS_REFERENCE_RELAY_SIGNING_SECRET", "").strip()
    if not public_base_url or not upload_token or not signing_secret:
        raise ReferenceRelayError(
            "reference relay requires public URL, upload token, and signing secret"
        )
    root = args.data_dir.resolve()
    store = SignedReferenceRelayStore(
        root / "reference-relay.sqlite3",
        root / "blobs",
        public_base_url=public_base_url,
        signing_secret=signing_secret,
    )
    access_ledger = ReferenceRelayAccessLedger(root / "reference-relay-access.sqlite3")
    server = ReferenceRelayHTTPServer(
        (args.host, args.port),
        store=store,
        access_ledger=access_ledger,
        upload_token=upload_token,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
