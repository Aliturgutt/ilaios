"""Production composition command using provider-neutral local adapters."""

from __future__ import annotations

import http.client
import os
import threading
from collections.abc import Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from services.control_plane.server import main as control_plane_main
from services.rag14_embedding_provider import (
    PRODUCTION_EMBEDDING_MODE,
    VERIFICATION_EMBEDDING_MODE,
)


_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
_ALLOWED_EMBEDDING_MODES = {
    VERIFICATION_EMBEDDING_MODE,
    PRODUCTION_EMBEDDING_MODE,
}


class _ReverseProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    upstream_host: str
    upstream_port: int


class _ReverseProxyHandler(BaseHTTPRequestHandler):
    server: _ReverseProxyServer

    def do_GET(self) -> None:
        self._proxy()

    def do_POST(self) -> None:
        self._proxy()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _proxy(self) -> None:
        raw_length = self.headers.get("Content-Length")
        body = b"" if raw_length is None else self.rfile.read(int(raw_length))
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in _HOP_BY_HOP_HEADERS and key.lower() != "host"
        }
        connection = http.client.HTTPConnection(
            self.server.upstream_host, self.server.upstream_port, timeout=10
        )
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in _HOP_BY_HOP_HEADERS and key.lower() != "content-length":
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        finally:
            connection.close()


def _knowledge_arguments(state_root: Path) -> tuple[str, ...]:
    values = {
        "principal": os.environ.get("ILAIOS_KNOWLEDGE_PRINCIPAL_ID", ""),
        "tenant": os.environ.get("ILAIOS_KNOWLEDGE_TENANT_ID", ""),
        "project": os.environ.get("ILAIOS_KNOWLEDGE_PROJECT_ID", ""),
        "classifications": os.environ.get("ILAIOS_KNOWLEDGE_CLASSIFICATIONS", ""),
        "purposes": os.environ.get("ILAIOS_KNOWLEDGE_PURPOSES", ""),
        "residencies": os.environ.get("ILAIOS_KNOWLEDGE_RESIDENCIES", ""),
        "embedding_mode": os.environ.get("ILAIOS_KNOWLEDGE_EMBEDDING_MODE", ""),
    }
    enabled = any(values.values())
    if not enabled:
        return ()
    if not all(values.values()):
        raise ValueError("all ILAIOS_KNOWLEDGE_* policy variables are required when enabled")
    if values["embedding_mode"] not in _ALLOWED_EMBEDDING_MODES:
        raise ValueError("configured Knowledge embedding mode is not implemented")
    release_state = os.environ.get("ILAIOS_RELEASE_STATE", "NOT_DEPLOYED")
    if release_state not in {"NOT_DEPLOYED", "CANARY", "LIMITED", "PRODUCTION"}:
        raise ValueError("Knowledge runtime received an unsupported release state")
    if (
        release_state == "PRODUCTION"
        and values["embedding_mode"] != PRODUCTION_EMBEDDING_MODE
    ):
        raise ValueError(
            "Knowledge production requires the pinned certified production embedding provider"
        )
    knowledge_root = state_root / "knowledge"
    return (
        "--knowledge-database",
        str(knowledge_root / "knowledge.sqlite3"),
        "--knowledge-vector-database",
        str(knowledge_root / "vectors.sqlite3"),
        "--knowledge-principal-id",
        values["principal"],
        "--knowledge-tenant-id",
        values["tenant"],
        "--knowledge-project-id",
        values["project"],
        "--knowledge-classifications",
        values["classifications"],
        "--knowledge-purposes",
        values["purposes"],
        "--knowledge-residencies",
        values["residencies"],
    )


def _control_plane_arguments(
    state_root: Path, ready_file_raw: str, *, host: str, port: str
) -> tuple[str, ...]:
    return (
        "--database",
        str(state_root / "control.sqlite3"),
        "--host",
        host,
        "--port",
        port,
        "--ready-file",
        ready_file_raw,
        "--evidence-root",
        str(state_root / "evidence"),
        "--governance-database",
        str(state_root / "governance.sqlite3"),
        "--hard-cap-minor",
        os.environ.get("ILAIOS_HARD_CAP_MINOR", "100"),
        "--video-root",
        str(state_root / "video"),
        "--product-proof-database",
        str(state_root / "product-proof.sqlite3"),
        *_knowledge_arguments(state_root),
    )


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        raise ValueError("production runtime accepts configuration through environment")
    state_root_raw = os.environ.get("ILAIOS_STATE_ROOT", "")
    ready_file_raw = os.environ.get("ILAIOS_READY_FILE", "")
    if not state_root_raw or not ready_file_raw:
        raise ValueError("ILAIOS_STATE_ROOT and ILAIOS_READY_FILE are required")
    state_root = Path(state_root_raw)
    if not state_root.is_absolute():
        raise ValueError("ILAIOS_STATE_ROOT must be absolute")
    state_root.mkdir(parents=True, exist_ok=True)

    maintenance_mode = os.environ.get("ILAIOS_RAG14_MAINTENANCE_MODE", "").strip()
    if maintenance_mode:
        from services.rag14_maintenance import main as rag14_maintenance_main

        return rag14_maintenance_main()

    requested_host = os.environ.get("ILAIOS_HOST", "127.0.0.1")
    requested_port = os.environ.get("ILAIOS_PORT", "0")
    if requested_host != "0.0.0.0":
        return control_plane_main(
            _control_plane_arguments(
                state_root, ready_file_raw, host=requested_host, port=requested_port
            )
        )

    external_port = int(requested_port)
    if not 1 <= external_port <= 65535:
        raise ValueError("non-loopback runtime exposure requires an explicit TCP port")
    internal_port = int(os.environ.get("ILAIOS_INTERNAL_PORT", "18080"))
    if not 1 <= internal_port <= 65535 or internal_port == external_port:
        raise ValueError("ILAIOS_INTERNAL_PORT must be a distinct valid TCP port")

    proxy = _ReverseProxyServer((requested_host, external_port), _ReverseProxyHandler)
    proxy.upstream_host = "127.0.0.1"
    proxy.upstream_port = internal_port
    thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    thread.start()
    try:
        return control_plane_main(
            _control_plane_arguments(
                state_root,
                ready_file_raw,
                host="127.0.0.1",
                port=str(internal_port),
            )
        )
    finally:
        proxy.shutdown()
        proxy.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
