"""Technology-neutral infrastructure and non-authoritative telemetry contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol


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

    def authorize(self, *_: object) -> None:
        raise ObservabilityError("telemetry cannot authorize")

    def canonical_evidence(self, *_: object) -> None:
        raise ObservabilityError("telemetry requires governed evidence admission")


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
