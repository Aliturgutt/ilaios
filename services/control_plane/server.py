"""Authenticated loopback HTTP process for the authoritative control plane."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from services.control_plane.api import (
    AuthenticationError,
    ControlPlane,
    ControlPlaneConfig,
    ControlPlaneError,
    GoalRecord,
    JobRecord,
)
from services.control_plane.migrations import current_schema_version


class ControlPlaneHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying its authoritative control-plane dependency."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        control_plane: ControlPlane,
    ) -> None:
        super().__init__(server_address, ControlPlaneRequestHandler)
        self.control_plane = control_plane


class ControlPlaneRequestHandler(BaseHTTPRequestHandler):
    """Versioned JSON command/query/event transport."""

    server: ControlPlaneHTTPServer

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/health/live":
                self._send_json(HTTPStatus.OK, {"status": "live"})
                return
            token = self._bearer_token()
            if path == "/v1/events":
                events = self.server.control_plane.list_events(token)
                self._send_json(HTTPStatus.OK, {"events": events})
                return
            resource, identifier = self._resource_path(path)
            if resource == "goals":
                self._send_json(
                    HTTPStatus.OK,
                    _record_json(self.server.control_plane.get_goal(token, identifier)),
                )
                return
            if resource == "jobs":
                self._send_json(
                    HTTPStatus.OK,
                    _record_json(self.server.control_plane.get_job(token, identifier)),
                )
                return
            self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except AuthenticationError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ControlPlaneError as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def do_POST(self) -> None:
        try:
            token = self._bearer_token()
            body = self._read_json()
            path = urlparse(self.path).path
            record: GoalRecord | JobRecord
            if path == "/v1/goals":
                objective = _required_string(body, "objective")
                record = self.server.control_plane.create_goal(token, objective)
            elif path == "/v1/jobs":
                goal_id = _required_string(body, "goal_id")
                record = self.server.control_plane.create_job(token, goal_id)
            else:
                self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                return
            self._send_json(HTTPStatus.CREATED, _record_json(record))
        except AuthenticationError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ControlPlaneError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def log_message(self, message_format: str, *args: object) -> None:
        print(
            json.dumps(
                {
                    "client": self.client_address[0],
                    "message": message_format % args,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    def _bearer_token(self) -> str:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            raise AuthenticationError("missing bearer token")
        return header[len(prefix) :]

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        length = int(raw_length)
        if length < 1 or length > 1_048_576:
            raise ValueError("request body length is outside allowed bounds")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise TypeError("request body must be a JSON object")
        return cast(dict[str, Any], value)

    @staticmethod
    def _resource_path(path: str) -> tuple[str, str]:
        parts = path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "v1" or parts[1] not in {"goals", "jobs"}:
            raise ValueError("invalid resource path")
        if not parts[2]:
            raise ValueError("resource identifier is required")
        return parts[1], parts[2]

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _record_json(record: GoalRecord | JobRecord) -> dict[str, Any]:
    if isinstance(record, GoalRecord):
        values: dict[str, Any] = {
            "goal_id": record.goal_id,
            "objective": record.objective,
            "created_at": record.created_at,
        }
    else:
        values = {
            "job_id": record.job_id,
            "goal_id": record.goal_id,
            "state": record.state,
            "created_at": record.created_at,
        }
    return {
        key: value.isoformat() if isinstance(value, datetime) else getattr(value, "value", value)
        for key, value in values.items()
    }


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    """Start the loopback service using explicit configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--ready-file", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("control plane must bind to a loopback host")
    token = os.environ.get("ILAIOS_CONTROL_PLANE_TOKEN", "")
    control_plane = ControlPlane(ControlPlaneConfig(arguments.database, token))
    server = ControlPlaneHTTPServer((arguments.host, arguments.port), control_plane)
    host, port = server.server_address[:2]
    ready = {
        "host": host,
        "port": port,
        "schema_version": current_schema_version(arguments.database),
    }
    arguments.ready_file.parent.mkdir(parents=True, exist_ok=True)
    arguments.ready_file.write_text(json.dumps(ready, sort_keys=True), encoding="utf-8")
    print(json.dumps({"event": "ready", **ready}, sort_keys=True), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
