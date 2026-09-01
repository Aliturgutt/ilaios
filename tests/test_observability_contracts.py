"""Bounded proofs for OBS.I06."""

from datetime import datetime, timezone

import pytest

from services.observability import (
    EvidenceAdmission,
    GovernedTelemetryAdmission,
    InfrastructureCapability,
    InfrastructureKind,
    ObservabilityError,
    SignalKind,
    TelemetrySignal,
    TelemetryStore,
)

NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _signal(kind: SignalKind = SignalKind.LOG) -> TelemetrySignal:
    return TelemetrySignal(
        "signal-1",
        kind,
        "api",
        "tenant-a",
        "correlation-1",
        NOW,
        "request.completed",
        "1",
        (("region", "eu"),),
    )


def test_portable_infrastructure_capabilities_are_vendor_neutral_and_tenant_aware() -> (
    None
):
    capabilities = tuple(
        InfrastructureCapability(
            f"cap-{kind.value}",
            kind,
            "replaceable-adapter",
            "v1",
            True,
            kind not in {InfrastructureKind.OCI_WORKLOAD, InfrastructureKind.INGRESS},
        )
        for kind in InfrastructureKind
    )
    assert {item.kind for item in capabilities} == set(InfrastructureKind)
    assert all(item.tenant_aware for item in capabilities)


def test_logs_metrics_traces_capacity_cost_and_health_remain_tenant_correlated() -> (
    None
):
    store = TelemetryStore()
    for kind in SignalKind:
        signal = _signal(kind)
        store.emit(
            TelemetrySignal(
                f"signal-{kind.value}",
                signal.kind,
                signal.service_id,
                signal.tenant_id,
                signal.correlation_id,
                signal.occurred_at,
                signal.name,
                signal.value,
                signal.attributes,
            )
        )
    assert len(store.correlated("correlation-1", "tenant-a")) == len(SignalKind)
    assert store.correlated("correlation-1", "tenant-b") == ()


def test_telemetry_cannot_authorize_or_become_evidence_implicitly() -> None:
    store = TelemetryStore()
    signal = _signal()
    store.emit(signal)
    with pytest.raises(ObservabilityError, match="cannot authorize"):
        store.authorize(signal)
    with pytest.raises(ObservabilityError, match="governed evidence"):
        store.canonical_evidence(signal)
    admission = EvidenceAdmission(
        "admission-1",
        signal.signal_id,
        "policy-v1",
        "verifier-1",
        NOW,
        "evidence://immutable/object-1",
    )
    GovernedTelemetryAdmission().admit(signal, admission)


def test_sensitive_attributes_are_rejected() -> None:
    with pytest.raises(ObservabilityError, match="sensitive"):
        TelemetrySignal(
            "signal-1",
            SignalKind.LOG,
            "api",
            "tenant-a",
            "correlation-1",
            NOW,
            "request",
            "1",
            (("token", "do-not-log"),),
        )
