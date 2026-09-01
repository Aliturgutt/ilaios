"""Runnable non-authoritative Web Control Center and service proxy."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_INDEX = b"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>ILAIOS Control Center</title></head>
<body><main><h1>ILAIOS Control Center</h1><p id="status">Connecting...</p>
<form id="goal"><input name="objective" required><button>Create goal</button></form>
<pre id="events"></pre></main><script>
async function refresh(){const r=await fetch('/api/events');document.querySelector('#status').textContent=r.ok?'Connected':'Denied';document.querySelector('#events').textContent=JSON.stringify(await r.json(),null,2)}
document.querySelector('#goal').addEventListener('submit',async(e)=>{e.preventDefault();await fetch('/api/goals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({objective:new FormData(e.target).get('objective')})});await refresh()});refresh();
</script></body></html>"""


class WebControlServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        upstream_ready_file: Path,
        token: str,
    ) -> None:
        super().__init__(address, WebControlHandler)
        self.upstream_ready_file = upstream_ready_file
        self.token = token


class WebControlHandler(BaseHTTPRequestHandler):
    server: WebControlServer

    def do_GET(self) -> None:
        if self.path == "/":
            self._send(HTTPStatus.OK, _INDEX, "text/html; charset=utf-8")
            return
        mapping = {"/api/events": "/v1/events"}
        upstream = mapping.get(self.path)
        if upstream is None:
            self._json_error(HTTPStatus.NOT_FOUND, "unknown web endpoint")
            return
        self._proxy("GET", upstream, None)

    def do_POST(self) -> None:
        mapping = {"/api/goals": "/v1/goals", "/api/jobs": "/v1/jobs"}
        upstream = mapping.get(self.path)
        if upstream is None:
            self._json_error(HTTPStatus.NOT_FOUND, "unknown web endpoint")
            return
        raw_length = self.headers.get("Content-Length")
        if raw_length is None or not raw_length.isdigit():
            self._json_error(HTTPStatus.BAD_REQUEST, "Content-Length is required")
            return
        length = int(raw_length)
        if length < 1 or length > 1_048_576:
            self._json_error(HTTPStatus.BAD_REQUEST, "invalid request size")
            return
        self._proxy("POST", upstream, self.rfile.read(length))

    def _proxy(self, method: str, path: str, body: bytes | None) -> None:
        try:
            ready = json.loads(self.server.upstream_ready_file.read_text())
            base_url = f"http://{ready['host']}:{ready['port']}"
            request = Request(
                base_url + path,
                data=body,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.server.token}",
                    "Content-Type": "application/json",
                },
            )
            try:
                response = urlopen(request, timeout=10)
            except HTTPError as error:
                self._send(HTTPStatus(error.code), error.read(), "application/json")
                return
            with response:
                self._send(
                    HTTPStatus(response.status), response.read(), "application/json"
                )
        except (FileNotFoundError, KeyError, json.JSONDecodeError, URLError):
            self._json_error(HTTPStatus.SERVICE_UNAVAILABLE, "control plane unavailable")

    def _json_error(self, status: HTTPStatus, message: str) -> None:
        self._send(
            status,
            json.dumps({"error": message}, sort_keys=True).encode(),
            "application/json",
        )

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, message_format: str, *args: object) -> None:
        return


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--upstream-ready-file", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("web control center must bind to loopback")
    token = os.environ.get("ILAIOS_WEB_CONTROL_TOKEN", "")
    if not token:
        parser.error("ILAIOS_WEB_CONTROL_TOKEN is required")
    server = WebControlServer(
        (arguments.host, arguments.port), arguments.upstream_ready_file, token
    )
    host, port = server.server_address[:2]
    arguments.ready_file.write_text(
        json.dumps({"host": host, "port": port}, sort_keys=True), encoding="utf-8"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
