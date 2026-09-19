"""Evidence-oriented bottleneck detection for proposed system architectures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BottleneckInput:
    """Measured or estimated utilization signals for one architecture review."""

    app_utilization: float | None = None
    database_utilization: float | None = None
    database_connection_utilization: float | None = None
    cache_hit_ratio: float | None = None
    queue_oldest_message_seconds: float | None = None
    queue_slo_seconds: float | None = None
    provider_quota_utilization: float | None = None
    network_utilization: float | None = None
    single_failure_domain: bool = False


@dataclass(frozen=True, slots=True)
class Bottleneck:
    code: str
    severity: str
    component: str
    evidence: str
    recommendation: str


def _ratio_issue(
    value: float | None,
    *,
    warning: float,
    critical: float,
    code: str,
    component: str,
    label: str,
) -> Bottleneck | None:
    if value is None:
        return None
    if not 0 <= value <= 1:
        raise ValueError(f"{label} must be in [0, 1]")
    if value < warning:
        return None
    severity = "critical" if value >= critical else "warning"
    return Bottleneck(
        code=code,
        severity=severity,
        component=component,
        evidence=f"{label}={value:.3f}",
        recommendation="Measure saturation under representative load and add headroom "
        "before increasing traffic.",
    )


def detect_bottlenecks(data: BottleneckInput) -> tuple[Bottleneck, ...]:
    """Return deterministic warnings from supplied telemetry, never guessed metrics."""

    findings: list[Bottleneck] = []
    checks = (
        _ratio_issue(
            data.app_utilization,
            warning=0.70,
            critical=0.90,
            code="APP_SATURATION",
            component="application",
            label="app_utilization",
        ),
        _ratio_issue(
            data.database_utilization,
            warning=0.70,
            critical=0.90,
            code="DATABASE_SATURATION",
            component="database",
            label="database_utilization",
        ),
        _ratio_issue(
            data.database_connection_utilization,
            warning=0.75,
            critical=0.90,
            code="DATABASE_CONNECTION_PRESSURE",
            component="database",
            label="database_connection_utilization",
        ),
        _ratio_issue(
            data.provider_quota_utilization,
            warning=0.75,
            critical=0.90,
            code="PROVIDER_QUOTA_PRESSURE",
            component="provider",
            label="provider_quota_utilization",
        ),
        _ratio_issue(
            data.network_utilization,
            warning=0.70,
            critical=0.90,
            code="NETWORK_SATURATION",
            component="network",
            label="network_utilization",
        ),
    )
    findings.extend(item for item in checks if item is not None)

    if data.cache_hit_ratio is not None:
        if not 0 <= data.cache_hit_ratio <= 1:
            raise ValueError("cache_hit_ratio must be in [0, 1]")
        if data.cache_hit_ratio < 0.60:
            findings.append(
                Bottleneck(
                    code="LOW_CACHE_EFFECTIVENESS",
                    severity="warning",
                    component="cache",
                    evidence=f"cache_hit_ratio={data.cache_hit_ratio:.3f}",
                    recommendation=(
                        "Validate cache keying, TTLs and invalidation before "
                        "adding cache capacity."
                    ),
                )
            )

    if data.queue_oldest_message_seconds is not None:
        if data.queue_oldest_message_seconds < 0:
            raise ValueError("queue_oldest_message_seconds must be non-negative")
        if data.queue_slo_seconds is None or data.queue_slo_seconds <= 0:
            raise ValueError(
                "queue_slo_seconds must be positive when queue lag is supplied"
            )
        ratio = data.queue_oldest_message_seconds / data.queue_slo_seconds
        if ratio >= 1:
            findings.append(
                Bottleneck(
                    code="QUEUE_SLO_BREACH",
                    severity="critical",
                    component="queue",
                    evidence=(
                        "oldest_message_seconds="
                        f"{data.queue_oldest_message_seconds:.3f}; "
                        f"queue_slo_seconds={data.queue_slo_seconds:.3f}"
                    ),
                    recommendation="Scale consumers only after verifying downstream "
                    "capacity, retry amplification and poison-message handling.",
                )
            )
        elif ratio >= 0.70:
            findings.append(
                Bottleneck(
                    code="QUEUE_LAG_PRESSURE",
                    severity="warning",
                    component="queue",
                    evidence=f"queue_lag_slo_ratio={ratio:.3f}",
                    recommendation="Inspect consumer throughput and downstream latency "
                    "before the queue SLO is breached.",
                )
            )

    if data.single_failure_domain:
        findings.append(
            Bottleneck(
                code="SINGLE_FAILURE_DOMAIN",
                severity="critical",
                component="availability",
                evidence="single_failure_domain=true",
                recommendation=(
                    "Distribute critical capacity across independent failure domains "
                    "when the availability requirement demands it."
                ),
            )
        )

    return tuple(findings)
