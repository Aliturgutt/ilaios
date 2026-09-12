"""Technology-neutral infrastructure and non-authoritative telemetry contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol
from uuid import uuid4


class ObservabilityError(RuntimeError):
    """Telemetry or infrastructure contract validation failed."""


class InfrastructureKind(str, Enum):
    OCI_WORKLOAD = "oci_workload"
    RELATIONAL_STORE = "relational_store"
    OBJECT_STORE = "object_store"
    QUEUE = "queue"
    PRIVATE_NETWORK = "private_network"
    INGRESS = "ingress"


@dataclass(frozen=True, slots=True)
class InfrastructureCapability:
    capability_id: str
    kind: InfrastructureKind
    adapter_id: str
    portable_contract_version: str
    tenant_aware: bool
    durable: bool


class InfrastructureAdapter(Protocol):
    @property
    def capability(self) -> InfrastructureCapability: ...

    def health(self, correlation_id: str) -> bool: ...


class SignalKind(str, Enum):
    LOG = "log"
    METRIC = "metric"
    TRACE = "trace"
    HEALTH = "health"
    CAPACITY = "capacity"
    COST = "cost"
    SECURITY = "security"


@dataclass(frozen=True, slots=True)
class TelemetrySignal:
    signal_id: str
    kind: SignalKind
    service_id: str
    tenant_id: str | None
    correlation_id: str
    occurred_at: datetime
    name: str
    value: str
    attributes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not all((self.signal_id, self.service_id, self.correlation_id, self.name)):
            raise ValueError("telemetry identity and correlation are required")
        forbidden = {"authorization", "password", "secret", "token", "cookie"}
        if any(key.lower() in forbidden for key, _ in self.attributes):
            raise ObservabilityError("sensitive telemetry attribute is prohibited")


class TelemetryStore:
    """Central structured telemetry; explicitly not authorization or evidence."""

    def __init__(self) -> None:
        self._signals: list[TelemetrySignal] = []

    def emit(self, signal: TelemetrySignal) -> None:
        self._signals.append(signal)

    def correlated(
        self, correlation_id: str, tenant_id: str | None
    ) -> tuple[TelemetrySignal, ...]:
        return tuple(
            signal
            for signal in self._signals
            if signal.correlation_id == correlation_id and signal.tenant_id == tenant_id
        )

    def named(
        self, name: str, tenant_id: str | None
    ) -> tuple[TelemetrySignal, ...]:
        return tuple(
            signal
            for signal in self._signals
            if signal.name == name and signal.tenant_id == tenant_id
        )

    def authorize(self, *_: object) -> None:
        raise ObservabilityError("telemetry cannot authorize")

    def canonical_evidence(self, *_: object) -> None:
        raise ObservabilityError("telemetry requires governed evidence admission")


_PROMPT_MODES = frozenset(
    {"improve", "clarify", "structure", "preserve-intent", "compress", "evaluate"}
)
_PROMPT_STATUSES = frozenset({"success", "validation_error", "internal_error"})
_SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")


class PromptRefinementTelemetry:
    """Privacy-safe Prompt Refinement metrics backed by canonical telemetry."""

    signal_name = "prompt.refinement.request"
    contract_version = "1"

    def __init__(self, store: TelemetryStore, *, source_sha: str = "unbound") -> None:
        if source_sha != "unbound" and _SOURCE_SHA.fullmatch(source_sha) is None:
            raise ObservabilityError("prompt telemetry source SHA is invalid")
        self._store = store
        self._source_sha = source_sha

    def record(
        self,
        *,
        mode: str,
        transformed: bool,
        issue_count: int,
        ambiguity_detected: bool,
        constraints_detected: bool,
        risk_cues_preserved: bool | None,
        factory_metadata_complete: bool,
        latency_ms: int,
        status: str,
    ) -> None:
        if mode not in _PROMPT_MODES:
            raise ObservabilityError("prompt telemetry mode is invalid")
        if status not in _PROMPT_STATUSES:
            raise ObservabilityError("prompt telemetry status is invalid")
        if issue_count < 0 or issue_count > 100:
            raise ObservabilityError("prompt telemetry issue count is outside bounds")
        if latency_ms < 0 or latency_ms > 3_600_000:
            raise ObservabilityError("prompt telemetry latency is outside bounds")
        attributes = (
            ("mode", mode),
            ("transformed", str(transformed).lower()),
            ("issue_count", str(issue_count)),
            ("ambiguity_detected", str(ambiguity_detected).lower()),
            ("constraints_detected", str(constraints_detected).lower()),
            (
                "risk_cues_preserved",
                "unknown"
                if risk_cues_preserved is None
                else str(risk_cues_preserved).lower(),
            ),
            ("factory_metadata_complete", str(factory_metadata_complete).lower()),
            ("latency_ms", str(latency_ms)),
            ("status", status),
            ("contract_version", self.contract_version),
            ("source_sha", self._source_sha),
        )
        self._store.emit(
            TelemetrySignal(
                signal_id=f"prompt-refinement-{uuid4().hex}",
                kind=SignalKind.METRIC,
                service_id="control-plane",
                tenant_id=None,
                correlation_id=uuid4().hex,
                occurred_at=datetime.now(timezone.utc),
                name=self.signal_name,
                value="1",
                attributes=attributes,
            )
        )

    def snapshot(self) -> dict[str, object]:
        signals = self._store.named(self.signal_name, None)
        by_mode = {mode: 0 for mode in sorted(_PROMPT_MODES)}
        transformed = 0
        failures = 0
        for signal in signals:
            attributes = dict(signal.attributes)
            mode = attributes["mode"]
            by_mode[mode] += 1
            if attributes["transformed"] == "true":
                transformed += 1
            if attributes["status"] != "success":
                failures += 1
        return {
            "contract_version": self.contract_version,
            "source_sha": self._source_sha,
            "requests": len(signals),
            "transformed": transformed,
            "failures": failures,
            "by_mode": by_mode,
        }


@dataclass(frozen=True, slots=True)
class EvidenceAdmission:
    admission_id: str
    signal_id: str
    policy_version: str
    admitted_by: str
    verified_at: datetime
    immutable_evidence_reference: str


class GovernedTelemetryAdmission:
    """Explicit bridge; admission creates a reference, never mutates telemetry."""

    def __init__(self) -> None:
        self._admissions: dict[str, EvidenceAdmission] = {}

    def admit(self, signal: TelemetrySignal, admission: EvidenceAdmission) -> None:
        if signal.signal_id != admission.signal_id:
            raise ObservabilityError("admission does not match telemetry signal")
        if not all(
            (
                admission.policy_version,
                admission.admitted_by,
                admission.immutable_evidence_reference,
            )
        ):
            raise ObservabilityError("governed admission metadata is incomplete")
        if admission.admission_id in self._admissions:
            raise ObservabilityError("evidence admission already exists")
        self._admissions[admission.admission_id] = admission
