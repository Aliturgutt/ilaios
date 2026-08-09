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
from urllib.parse import parse_qs, urlparse

from services.control_plane.api import (
    AuthenticationError,
    ControlPlane,
    ControlPlaneConfig,
    ControlPlaneError,
    GoalRecord,
    JobRecord,
)
from services.control_plane.migrations import current_schema_version
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    ProposedTask,
    RiskClass,
)
from services.control_plane.workflows import (
    AttemptRecord,
    WorkflowError,
    WorkflowStore,
    WorkflowStoreConfig,
)


class ControlPlaneHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying its authoritative control-plane dependency."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        control_plane: ControlPlane,
        workflow_store: WorkflowStore,
    ) -> None:
        super().__init__(server_address, ControlPlaneRequestHandler)
        self.control_plane = control_plane
        self.workflow_store = workflow_store


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
            if path == "/v1/workflow/outbox":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "events": [
                            {
                                "sequence": event.sequence,
                                "event_id": event.event_id,
                                "event_type": event.event_type,
                                "payload": event.payload,
                            }
                            for event in self.server.workflow_store.pending_outbox()
                        ]
                    },
                )
                return
            if path == "/v1/workflow/checkpoint":
                query = parse_qs(urlparse(self.path).query)
                attempt_id = _single_query_value(query, "attempt_id")
                key = _single_query_value(query, "key")
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "payload": self.server.workflow_store.load_checkpoint(
                            attempt_id, key
                        )
                    },
                )
                return
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
            if resource == "proposals":
                self._send_json(
                    HTTPStatus.OK,
                    self.server.control_plane.get_proposal(token, identifier),
                )
                return
            self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except AuthenticationError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ControlPlaneError as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
        except WorkflowError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def do_POST(self) -> None:
        try:
            token = self._bearer_token()
            body = self._read_json()
            path = urlparse(self.path).path
            if path == "/v1/workflow/commands":
                self._send_json(HTTPStatus.OK, self._workflow_command(body))
                return
            record: GoalRecord | JobRecord
            if path == "/v1/goals":
                objective = _required_string(body, "objective")
                record = self.server.control_plane.create_goal(token, objective)
            elif path == "/v1/jobs":
                goal_id = _required_string(body, "goal_id")
                record = self.server.control_plane.create_job(token, goal_id)
            elif path == "/v1/proposals":
                proposal = self.server.control_plane.create_proposal(
                    token,
                    _required_string(body, "goal_id"),
                    acceptance_criteria=_string_tuple(body, "acceptance_criteria"),
                    risk_class=RiskClass(_required_string(body, "risk_class")),
                    data_class=DataClass(_required_string(body, "data_class")),
                    budget=_budget(body),
                    tasks=_tasks(body),
                )
                self._send_json(HTTPStatus.CREATED, proposal)
                return
            else:
                self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                return
            self._send_json(HTTPStatus.CREATED, _record_json(record))
        except AuthenticationError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ControlPlaneError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except WorkflowError as error:
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
        if (
            len(parts) != 3
            or parts[0] != "v1"
            or parts[1] not in {"goals", "jobs", "proposals"}
        ):
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

    def _workflow_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = _required_string(payload, "operation")
        store = self.server.workflow_store
        if operation == "create_workflow":
            workflow_id = _required_string(payload, "workflow_id")
            store.create_workflow(workflow_id)
            return {"workflow_id": workflow_id, "status": "active"}
        if operation == "add_task":
            workflow_id = _required_string(payload, "workflow_id")
            task_id = _required_string(payload, "task_id")
            store.add_task(
                workflow_id,
                task_id,
                max_attempts=_required_int(payload, "max_attempts"),
                compensation_event_type=_optional_string(
                    payload, "compensation_event_type"
                ),
            )
            return {"workflow_id": workflow_id, "task_id": task_id, "status": "ready"}
        if operation == "begin_attempt":
            attempt = store.begin_attempt(
                _required_string(payload, "workflow_id"),
                _required_string(payload, "task_id"),
                deadline=_required_datetime(payload, "deadline"),
            )
            return _attempt_json(attempt)
        if operation == "save_checkpoint":
            store.save_checkpoint(
                _required_string(payload, "attempt_id"),
                _required_string(payload, "key"),
                _required_object(payload, "payload"),
            )
            return {"saved": True}
        if operation == "fail_attempt":
            status = store.fail_attempt(
                _required_string(payload, "attempt_id"),
                reason=_required_string(payload, "reason"),
            )
            return {"task_status": status}
        if operation == "timeout_attempt":
            status = store.timeout_attempt(
                _required_string(payload, "attempt_id"),
                now=_required_datetime(payload, "now"),
            )
            return {"task_status": status}
        if operation == "complete_attempt":
            store.complete_attempt(_required_string(payload, "attempt_id"))
            return {"task_status": "completed"}
        if operation == "receive_event":
            accepted = store.receive_event(
                _required_string(payload, "event_id"),
                _required_object(payload, "payload"),
            )
            return {"accepted": accepted}
        if operation == "acknowledge_outbox":
            store.acknowledge_outbox(_required_string(payload, "event_id"))
            return {"acknowledged": True}
        raise ValueError("unknown workflow operation")


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


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string or null")
    return value


def _required_datetime(payload: dict[str, Any], key: str) -> datetime:
    value = _required_string(payload, key)
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError(f"{key} must include a timezone")
    return result


def _single_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key, [])
    if len(values) != 1 or not values[0]:
        raise ValueError(f"exactly one {key} query value is required")
    return values[0]


def _attempt_json(attempt: AttemptRecord) -> dict[str, Any]:
    return {
        "attempt_id": attempt.attempt_id,
        "workflow_id": attempt.workflow_id,
        "task_id": attempt.task_id,
        "number": attempt.number,
        "status": attempt.status,
        "deadline": attempt.deadline.isoformat(),
    }


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{key} must be an integer")
    return value


def _required_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be an object")
    return cast(dict[str, Any], value)


def _string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TypeError(f"{key} must be an array of strings")
    return tuple(value)


def _budget(payload: dict[str, Any]) -> BudgetEnvelope:
    value = _required_object(payload, "budget")
    return BudgetEnvelope(
        max_attempts=_required_int(value, "max_attempts"),
        max_runtime_seconds=_required_int(value, "max_runtime_seconds"),
        max_external_spend_minor=_required_int(value, "max_external_spend_minor"),
    )


def _tasks(payload: dict[str, Any]) -> tuple[ProposedTask, ...]:
    value = payload.get("tasks")
    if not isinstance(value, list):
        raise TypeError("tasks must be an array")
    tasks: list[ProposedTask] = []
    for raw_task in value:
        if not isinstance(raw_task, dict):
            raise TypeError("each task must be an object")
        task = cast(dict[str, Any], raw_task)
        tasks.append(
            ProposedTask(
                task_id=_required_string(task, "task_id"),
                responsibility=_required_string(task, "responsibility"),
                dependencies=_string_tuple(task, "dependencies"),
            )
        )
    return tuple(tasks)


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
    workflow_store = WorkflowStore(WorkflowStoreConfig(arguments.database))
    server = ControlPlaneHTTPServer(
        (arguments.host, arguments.port), control_plane, workflow_store
    )
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
