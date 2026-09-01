"""Authenticated loopback HTTP process for the authoritative control plane."""

from __future__ import annotations

import argparse
import base64
import json
import os
from collections.abc import Sequence
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from services.control_plane.agent_api import canonical_agent_state, handle_agent_command
from services.control_plane.api import (
    AuthenticationError,
    ControlPlane,
    ControlPlaneConfig,
    ControlPlaneError,
    GoalRecord,
    JobRecord,
)
from services.control_plane.live_state import (
    LiveEvent,
    LiveStateError,
    LiveStateTransport,
)
from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    current_schema_version,
)
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
from services.evidence import EvidenceError, EvidenceStore, ProvenanceRecord
from services.governance import GateError, GovernedRuntimeGateway
from services.identity import IdentityError
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    ProductRuntimeError,
    VideoRuntimeError,
)
from services.knowledge_rag import KnowledgeRAGError
from services.knowledge_runtime import (
    DurableKnowledgeRuntime,
    KnowledgeRuntimeConfig,
    KnowledgeRuntimeError,
    KnowledgeRuntimePolicy,
)
from services.runtime import (
    BlastRadiusBudget,
    DurableGrantPolicy,
    DurableWorkerScheduler,
    ExecutionGrant,
    GovernedRuntime,
    GrantError,
    Lease,
    SchedulingError,
    WorkerProfile,
)
from services.runtime import RuntimeError as GovernedRuntimeError


class ControlPlaneHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying its authoritative control-plane dependency."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        control_plane: ControlPlane,
        workflow_store: WorkflowStore,
        live_state: LiveStateTransport,
        governed_runtime: GovernedRuntime,
        scheduler: DurableWorkerScheduler,
        grant_policy: DurableGrantPolicy,
        evidence_store: EvidenceStore,
        governance: GovernedRuntimeGateway,
        video_runtime: DeterministicLocalVideoRuntime,
        product_runtime: DurableVideoProductRuntime,
        knowledge_runtime: DurableKnowledgeRuntime | None = None,
    ) -> None:
        super().__init__(server_address, ControlPlaneRequestHandler)
        self.control_plane = control_plane
        self.workflow_store = workflow_store
        self.live_state = live_state
        self.governed_runtime = governed_runtime
        self.scheduler = scheduler
        self.grant_policy = grant_policy
        self.evidence_store = evidence_store
        self.governance = governance
        self.video_runtime = video_runtime
        self.product_runtime = product_runtime
        self.knowledge_runtime = knowledge_runtime


class ControlPlaneRequestHandler(BaseHTTPRequestHandler):
    """Versioned JSON command/query/event transport."""

    server: ControlPlaneHTTPServer

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/health/live":
                self._send_json(HTTPStatus.OK, {"status": "live"})
                return
            if path == "/health/ready":
                try:
                    schema_version = current_schema_version(
                        self.server.control_plane.database_path
                    )
                    self.server.evidence_store.verify()
                    if self.server.knowledge_runtime is not None:
                        self.server.knowledge_runtime.verify()
                except (
                    EvidenceError,
                    KnowledgeRAGError,
                    KnowledgeRuntimeError,
                    OSError,
                ):
                    self._send_json(
                        HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_ready"}
                    )
                    return
                ready = schema_version == LATEST_SCHEMA_VERSION
                self._send_json(
                    HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "status": "ready" if ready else "not_ready",
                        "schema_version": schema_version,
                        "dependencies": {
                            "artifact_store": "ready",
                            "control_database": "ready" if ready else "not_ready",
                            "knowledge_store": (
                                "ready"
                                if self.server.knowledge_runtime is not None
                                else "disabled"
                            ),
                        },
                    },
                )
                return
            token = self._bearer_token()
            self.server.control_plane.authenticate(token)
            if path == "/v1/knowledge/state":
                knowledge = self._require_knowledge_runtime()
                self._send_json(HTTPStatus.OK, knowledge.state())
                return
            if path == "/v1/knowledge/verify":
                knowledge = self._require_knowledge_runtime()
                self._send_json(HTTPStatus.OK, knowledge.verify())
                return
            if path == "/v1/live/events":
                query = parse_qs(urlparse(self.path).query)
                after_sequence = _optional_query_int(query, "after_sequence", default=0)
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "events": [
                            _live_event_json(event)
                            for event in self.server.live_state.replay(
                                after_sequence=after_sequence
                            )
                        ]
                    },
                )
                return
            if path == "/v1/runtime/routes":
                self._send_json(
                    HTTPStatus.OK,
                    {"routes": self.server.governed_runtime.routes()},
                )
                return
            if path == "/v1/agents/state":
                self._send_json(
                    HTTPStatus.OK,
                    canonical_agent_state(self.server.governed_runtime),
                )
                return
            if path == "/v1/scheduler/state":
                self._send_json(HTTPStatus.OK, self.server.scheduler.state())
                return
            if path == "/v1/grants/state":
                self._send_json(HTTPStatus.OK, self.server.grant_policy.state())
                return
            if path == "/v1/evidence/verify":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "records": [
                            _provenance_json(record)
                            for record in self.server.evidence_store.verify()
                        ]
                    },
                )
                return
            if path == "/v1/governance/state":
                self._send_json(HTTPStatus.OK, self.server.governance.state())
                return
            if path.startswith("/v1/video/deliveries/"):
                delivery_id = path.removeprefix("/v1/video/deliveries/")
                self._send_json(
                    HTTPStatus.OK, self.server.video_runtime.get_delivery(delivery_id)
                )
                return
            if path.startswith("/v1/product-proof/manifests/"):
                request_id = path.removeprefix("/v1/product-proof/manifests/")
                self._send_json(
                    HTTPStatus.OK, self.server.product_runtime.get_manifest(request_id)
                )
                return
            if path.startswith("/v1/evidence/artifacts/"):
                digest = path.removeprefix("/v1/evidence/artifacts/")
                content = self.server.evidence_store.get_artifact(digest)
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "digest": digest,
                        "size": len(content),
                        "content_base64": base64.b64encode(content).decode("ascii"),
                    },
                )
                return
            if path == "/v1/live/snapshot":
                query = parse_qs(urlparse(self.path).query)
                aggregate_id = _single_query_value(query, "aggregate_id")
                self._send_json(
                    HTTPStatus.OK,
                    _live_event_json(self.server.live_state.snapshot(aggregate_id)),
                )
                return
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
        except IdentityError as error:
            self._send_error(HTTPStatus.FORBIDDEN, str(error))
        except ControlPlaneError as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
        except WorkflowError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except LiveStateError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except GovernedRuntimeError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except SchedulingError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except GrantError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except EvidenceError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except GateError as error:
            self._send_error(HTTPStatus.FORBIDDEN, str(error))
        except VideoRuntimeError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except ProductRuntimeError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except (KnowledgeRAGError, KnowledgeRuntimeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def do_POST(self) -> None:
        try:
            token = self._bearer_token()
            self.server.control_plane.authenticate(token)
            body = self._read_json()
            path = urlparse(self.path).path
            if path == "/v1/knowledge/commands":
                self._send_json(HTTPStatus.OK, self._knowledge_command(body))
                return
            if path == "/v1/workflow/commands":
                self._send_json(HTTPStatus.OK, self._workflow_command(body))
                return
            if path == "/v1/live/events":
                event = self.server.live_state.publish(
                    _required_string(body, "aggregate_id"),
                    _required_string(body, "event_type"),
                    _required_object(body, "state"),
                )
                self._send_json(HTTPStatus.CREATED, _live_event_json(event))
                return
            if path == "/v1/runtime/commands":
                self._send_json(HTTPStatus.OK, self._runtime_command(body))
                return
            if path == "/v1/agents/commands":
                self._send_json(
                    HTTPStatus.OK,
                    handle_agent_command(self.server.governed_runtime, body),
                )
                return
            if path == "/v1/scheduler/commands":
                self._send_json(HTTPStatus.OK, self._scheduler_command(body))
                return
            if path == "/v1/grants/commands":
                self._send_json(HTTPStatus.OK, self._grant_command(body))
                return
            if path == "/v1/evidence/commands":
                self._send_json(HTTPStatus.CREATED, self._evidence_command(body))
                return
            if path == "/v1/governance/commands":
                self._send_json(HTTPStatus.OK, self._governance_command(body))
                return
            if path == "/v1/video/commands":
                self._send_json(HTTPStatus.OK, self._video_command(body))
                return
            if path == "/v1/product-proof/commands":
                self._send_json(
                    HTTPStatus.OK, self._product_proof_command(body, token=token)
                )
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
        except IdentityError as error:
            self._send_error(HTTPStatus.FORBIDDEN, str(error))
        except ControlPlaneError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except WorkflowError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except LiveStateError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except GovernedRuntimeError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except SchedulingError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except GrantError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except EvidenceError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except GateError as error:
            self._send_error(HTTPStatus.FORBIDDEN, str(error))
        except VideoRuntimeError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except ProductRuntimeError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except (KnowledgeRAGError, KnowledgeRuntimeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except (
            json.JSONDecodeError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
        ) as error:
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

    def _require_knowledge_runtime(self) -> DurableKnowledgeRuntime:
        runtime = self.server.knowledge_runtime
        if runtime is None:
            raise KnowledgeRuntimeError("knowledge runtime is disabled")
        return runtime

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _knowledge_command(self, payload: dict[str, Any]) -> dict[str, object]:
        if "tenant_id" in payload or "project_id" in payload:
            raise KnowledgeRuntimeError("tenant and project scope are server-resolved")
        runtime = self._require_knowledge_runtime()
        operation = _required_string(payload, "operation")
        if operation == "ingest_source":
            return runtime.ingest_source(
                source_id=_required_string(payload, "source_id"),
                locator=_required_string(payload, "locator"),
                content=_required_string(payload, "content"),
                trusted=_optional_bool(payload, "trusted", default=False),
                classifications=frozenset(_string_tuple(payload, "classifications")),
                purposes=frozenset(_string_tuple(payload, "purposes")),
                residency=_required_string(payload, "residency"),
            )
        if operation == "update_source":
            return runtime.update_source(
                source_id=_required_string(payload, "source_id"),
                content=_required_string(payload, "content"),
            )
        if operation == "revoke_source":
            return runtime.revoke_source(
                source_id=_required_string(payload, "source_id")
            )
        if operation == "delete_source":
            return runtime.delete_source(
                source_id=_required_string(payload, "source_id")
            )
        if operation == "retrieve":
            return runtime.retrieve(
                retrieval_id=_required_string(payload, "retrieval_id"),
                query=_required_string(payload, "query"),
                purpose=_required_string(payload, "purpose"),
                top_k=_required_int(payload, "top_k"),
                candidate_limit=_required_int(payload, "candidate_limit"),
                max_context_chars=_required_int(payload, "max_context_chars"),
            )
        raise ValueError("unknown knowledge operation")

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

    def _runtime_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = _required_string(payload, "operation")
        runtime = self.server.governed_runtime
        if operation == "register_agent":
            agent_id = _required_string(payload, "agent_id")
            runtime.register_agent(
                agent_id, frozenset(_string_tuple(payload, "authorities"))
            )
            return {"agent_id": agent_id, "registered": True}
        if operation == "register_skill":
            skill_id = _required_string(payload, "skill_id")
            try:
                content = base64.b64decode(
                    _required_string(payload, "content_base64"), validate=True
                )
            except ValueError as error:
                raise GovernedRuntimeError("skill content is not valid base64") from error
            digest = runtime.register_skill(
                skill_id,
                content,
                frozenset(_string_tuple(payload, "authorities")),
            )
            return {"skill_id": skill_id, "digest": digest, "registered": True}
        if operation == "register_provider":
            provider_id = _required_string(payload, "provider_id")
            runtime.register_provider(
                provider_id,
                frozenset(_string_tuple(payload, "capabilities")),
                adapter_kind=_required_string(payload, "adapter_kind"),
                enabled=_optional_bool(payload, "enabled", default=True),
            )
            return {"provider_id": provider_id, "registered": True}
        if operation == "execute":
            raise GateError("runtime execution requires governed work")
        raise ValueError("unknown runtime operation")

    def _scheduler_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = _required_string(payload, "operation")
        scheduler = self.server.scheduler
        if operation == "register_worker":
            worker_id = _required_string(payload, "worker_id")
            scheduler.register(
                WorkerProfile(
                    worker_id,
                    frozenset(_string_tuple(payload, "capabilities")),
                    _required_int(payload, "max_concurrent_tasks"),
                )
            )
            return {"worker_id": worker_id, "registered": True}
        if operation == "schedule":
            return _lease_json(
                scheduler.schedule(
                    _required_string(payload, "task_id"),
                    _required_string(payload, "capability"),
                    now=_required_datetime(payload, "now"),
                )
            )
        if operation == "reschedule_expired":
            return _lease_json(
                scheduler.reschedule_expired(
                    _required_string(payload, "task_id"),
                    _required_string(payload, "capability"),
                    now=_required_datetime(payload, "now"),
                )
            )
        if operation == "heartbeat":
            return _lease_json(
                scheduler.heartbeat(
                    _lease_from_payload(payload),
                    now=_required_datetime(payload, "now"),
                )
            )
        if operation == "record_side_effect":
            lease = _lease_from_payload(payload)
            now = _required_datetime(payload, "now")
            scheduler.authorize(lease, now=now)
            self.server.grant_policy.authorize_and_record(
                _required_string(payload, "grant_id"),
                subject_id=lease.worker_id,
                action="write",
                resource=lease.task_id,
                now=now,
            )
            scheduler.record_side_effect(
                lease,
                now=now,
                payload=_required_object(payload, "payload"),
            )
            return {"recorded": True}
        raise ValueError("unknown scheduler operation")

    def _grant_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = _required_string(payload, "operation")
        now = _required_datetime(payload, "now")
        if operation == "register":
            grant = ExecutionGrant(
                _required_string(payload, "grant_id"),
                _required_string(payload, "subject_id"),
                frozenset(_string_tuple(payload, "actions")),
                frozenset(_string_tuple(payload, "resources")),
                _required_datetime(payload, "expires_at"),
                BlastRadiusBudget(
                    _required_int(payload, "max_side_effects"),
                    _required_int(payload, "max_resources"),
                ),
            )
            self.server.grant_policy.register(grant)
            return {"grant_id": grant.grant_id, "registered": True}
        grant_id = _required_string(payload, "grant_id")
        if operation == "revoke":
            self.server.grant_policy.revoke(grant_id, now=now)
            return {"revoked": True}
        if operation == "kill":
            self.server.grant_policy.kill(
                _required_string(payload, "subject_id"), now=now
            )
            return {"stopped": True}
        raise ValueError("unknown grant operation")

    def _evidence_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = _required_string(payload, "operation")
        if operation != "store_execution_artifact":
            raise ValueError("unknown evidence operation")
        try:
            content = base64.b64decode(
                _required_string(payload, "content_base64"), validate=True
            )
        except ValueError as error:
            raise EvidenceError("artifact content is not valid base64") from error
        artifact = self.server.evidence_store.put_artifact(content)
        provenance = self.server.evidence_store.append_provenance(
            _required_string(payload, "execution_id"),
            artifact,
            _required_string(payload, "action"),
        )
        return {
            "artifact": {"digest": artifact.digest, "size": artifact.size},
            "provenance": _provenance_json(provenance),
        }

    def _governance_command(self, payload: dict[str, Any]) -> dict[str, object]:
        operation = _required_string(payload, "operation")
        gateway = self.server.governance
        if operation == "register_secret_reference":
            secret_id = _required_string(payload, "secret_id")
            gateway.register_secret_reference(
                secret_id, _required_string(payload, "reference")
            )
            return {"secret_id": secret_id, "registered": True}
        if operation == "submit":
            return gateway.submit(
                _required_string(payload, "request_id"),
                _required_string(payload, "requester_id"),
                _required_string(payload, "agent_id"),
                _required_string(payload, "skill_id"),
                _required_string(payload, "capability"),
                _required_object(payload, "payload"),
                _string_tuple(payload, "secret_ids"),
            )
        if operation == "decide":
            gateway.decide(
                _required_string(payload, "request_id"),
                _required_string(payload, "approver"),
                _required_string(payload, "decision"),
            )
            return {"decided": True}
        if operation == "execute":
            return gateway.execute(_required_string(payload, "request_id"))
        raise ValueError("unknown governance operation")

    def _video_command(self, payload: dict[str, Any]) -> dict[str, object]:
        if _required_string(payload, "operation") != "execute_local":
            raise ValueError("unknown video operation")
        return self.server.video_runtime.execute(
            request_id=_required_string(payload, "request_id"),
            job_id=_required_string(payload, "job_id"),
            grant_id=_required_string(payload, "grant_id"),
            now=_required_datetime(payload, "now"),
        )

    def _product_proof_command(
        self, payload: dict[str, Any], *, token: str
    ) -> dict[str, object]:
        operation = _required_string(payload, "operation")
        if operation == "prepare_windows_video":
            return self.server.product_runtime.prepare(
                _required_string(payload, "request_id"),
                _required_string(payload, "objective"),
                token=token,
                now=_required_datetime(payload, "now"),
            )
        if operation == "execute_windows_video":
            return self.server.product_runtime.execute(
                _required_string(payload, "request_id"),
                _required_string(payload, "grant_id"),
                token=token,
                now=_required_datetime(payload, "now"),
            )
        raise ValueError("unknown product-proof operation")


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


def _optional_query_int(
    query: dict[str, list[str]], key: str, *, default: int
) -> int:
    values = query.get(key)
    if values is None:
        return default
    if len(values) != 1:
        raise ValueError(f"at most one {key} query value is allowed")
    return int(values[0])


def _attempt_json(attempt: AttemptRecord) -> dict[str, Any]:
    return {
        "attempt_id": attempt.attempt_id,
        "workflow_id": attempt.workflow_id,
        "task_id": attempt.task_id,
        "number": attempt.number,
        "status": attempt.status,
        "deadline": attempt.deadline.isoformat(),
    }


def _live_event_json(event: LiveEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "aggregate_id": event.aggregate_id,
        "version": event.version,
        "event_type": event.event_type,
        "state": event.state,
    }


def _lease_from_payload(payload: dict[str, Any]) -> Lease:
    raw = _required_object(payload, "lease")
    return Lease(
        _required_string(raw, "task_id"),
        _required_string(raw, "worker_id"),
        _required_int(raw, "fencing_token"),
        _required_datetime(raw, "expires_at"),
    )


def _lease_json(lease: Lease) -> dict[str, Any]:
    return {
        "task_id": lease.task_id,
        "worker_id": lease.worker_id,
        "fencing_token": lease.fencing_token,
        "expires_at": lease.expires_at.isoformat(),
    }


def _provenance_json(record: ProvenanceRecord) -> dict[str, Any]:
    return {
        "sequence": record.sequence,
        "execution_id": record.execution_id,
        "artifact_digest": record.artifact_digest,
        "action": record.action,
        "previous_hash": record.previous_hash,
        "record_hash": record.record_hash,
    }


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{key} must be an integer")
    return value


def _optional_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a boolean")
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


def _csv_set(value: str) -> frozenset[str]:
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    if not items:
        raise KnowledgeRuntimeError("knowledge policy lists must not be empty")
    return frozenset(items)


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


def _write_ready_file_atomically(path: Path, ready: dict[str, object]) -> None:
    """Publish readiness only after a complete JSON document is durable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(ready, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    """Start the loopback service using explicit configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--governance-database", type=Path, required=True)
    parser.add_argument("--hard-cap-minor", type=int, default=100)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--product-proof-database", type=Path, required=True)
    parser.add_argument("--lease-seconds", type=int, default=30)
    parser.add_argument("--knowledge-database", type=Path)
    parser.add_argument("--knowledge-vector-database", type=Path)
    parser.add_argument("--knowledge-principal-id")
    parser.add_argument("--knowledge-tenant-id")
    parser.add_argument("--knowledge-project-id")
    parser.add_argument("--knowledge-classifications")
    parser.add_argument("--knowledge-purposes")
    parser.add_argument("--knowledge-residencies")
    arguments = parser.parse_args(argv)
    if arguments.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("control plane must bind to a loopback host")
    token = os.environ.get("ILAIOS_CONTROL_PLANE_TOKEN", "")
    control_plane = ControlPlane(ControlPlaneConfig(arguments.database, token))
    workflow_store = WorkflowStore(WorkflowStoreConfig(arguments.database))
    live_state = LiveStateTransport(arguments.database)
    governed_runtime = GovernedRuntime(arguments.database)
    scheduler = DurableWorkerScheduler(
        arguments.database, lease_duration=timedelta(seconds=arguments.lease_seconds)
    )
    grant_policy = DurableGrantPolicy(arguments.database)
    evidence_store = EvidenceStore(arguments.evidence_root)
    governance = GovernedRuntimeGateway(
        arguments.governance_database,
        governed_runtime,
        hard_cap_minor=arguments.hard_cap_minor,
    )
    video_runtime = DeterministicLocalVideoRuntime(
        arguments.video_root, grant_policy, governance, evidence_store
    )
    product_runtime = DurableVideoProductRuntime(
        arguments.product_proof_database,
        control_plane,
        workflow_store,
        scheduler,
        grant_policy,
        governance,
        video_runtime,
    )
    knowledge_values = (
        arguments.knowledge_database,
        arguments.knowledge_vector_database,
        arguments.knowledge_principal_id,
        arguments.knowledge_tenant_id,
        arguments.knowledge_project_id,
        arguments.knowledge_classifications,
        arguments.knowledge_purposes,
        arguments.knowledge_residencies,
    )
    knowledge_runtime: DurableKnowledgeRuntime | None = None
    if any(value is not None for value in knowledge_values):
        if any(value is None for value in knowledge_values):
            parser.error("all Knowledge runtime arguments are required when enabled")
        knowledge_runtime = DurableKnowledgeRuntime(
            KnowledgeRuntimeConfig(
                metadata_database=cast(Path, arguments.knowledge_database),
                vector_database=cast(Path, arguments.knowledge_vector_database),
                policy=KnowledgeRuntimePolicy(
                    principal_id=cast(str, arguments.knowledge_principal_id),
                    tenant_id=cast(str, arguments.knowledge_tenant_id),
                    project_id=cast(str, arguments.knowledge_project_id),
                    allowed_classifications=_csv_set(
                        cast(str, arguments.knowledge_classifications)
                    ),
                    allowed_purposes=_csv_set(cast(str, arguments.knowledge_purposes)),
                    allowed_residencies=_csv_set(
                        cast(str, arguments.knowledge_residencies)
                    ),
                ),
            )
        )
    server = ControlPlaneHTTPServer(
        (arguments.host, arguments.port),
        control_plane,
        workflow_store,
        live_state,
        governed_runtime,
        scheduler,
        grant_policy,
        evidence_store,
        governance,
        video_runtime,
        product_runtime,
        knowledge_runtime,
    )
    host, port = server.server_address[:2]
    ready: dict[str, object] = {
        "host": host,
        "port": port,
        "schema_version": current_schema_version(arguments.database),
        "knowledge_enabled": knowledge_runtime is not None,
    }
    _write_ready_file_atomically(arguments.ready_file, ready)
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
