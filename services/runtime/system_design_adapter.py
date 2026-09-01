"""First-party deterministic adapter for the governed ILAIOS system-design skill."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from services.runtime.routing import RuntimeError
from src.system_design.capacity_analyzer import CapacityInput
from src.system_design.pipeline import SystemDesignRequest, run_system_design

SYSTEM_DESIGN_AGENT_ID = "ilaios.agent.engineering.architect.v1"
SYSTEM_DESIGN_SKILL_ID = "ilaios.skill.system-design"
SYSTEM_DESIGN_CAPABILITY = "architecture.propose"
SYSTEM_DESIGN_PROVIDER_ID = "ilaios.provider.local.system-design.v1"
SYSTEM_DESIGN_ADAPTER_KIND = "ilaios-system-design-v1"


def execute_system_design_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate structured planner output and run deterministic design analysis."""
    if not isinstance(payload, dict):
        raise RuntimeError("system-design payload must be an object")
    system_id = _required_string(payload, "system_id")
    capacity_payload = payload.get("capacity")
    if not isinstance(capacity_payload, dict):
        raise RuntimeError("system-design payload requires a capacity object")
    try:
        capacity = CapacityInput(**capacity_payload)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"invalid system-design capacity input: {error}") from error
    availability_slo = _required_number(payload, "availability_slo")
    internet_facing = _optional_bool(payload, "internet_facing", True)
    asynchronous_fraction = _optional_number(
        payload, "asynchronous_workload_fraction", 0.0
    )
    latency_slo_ms = _optional_positive_int(payload, "latency_slo_ms")
    try:
        result = run_system_design(
            SystemDesignRequest(
                system_id=system_id,
                capacity=capacity,
                availability_slo=availability_slo,
                internet_facing=internet_facing,
                asynchronous_workload_fraction=asynchronous_fraction,
                latency_slo_ms=latency_slo_ms,
            )
        )
    except ValueError as error:
        raise RuntimeError(f"system-design analysis rejected input: {error}") from error
    return {
        "architecture": result.architecture,
        "capacity": asdict(result.capacity),
        "review_issue_codes": list(result.review_issue_codes),
        "evidence_required": list(result.evidence_required),
        "maturity": "IMPLEMENTED",
        "production_scale_verified": False,
    }


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise RuntimeError(f"{key} must be a non-blank trimmed string")
    return value


def _required_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{key} must be numeric")
    return float(value)


def _optional_number(payload: dict[str, Any], key: str, default: float) -> float:
    if key not in payload:
        return default
    return _required_number(payload, key)


def _optional_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    if key not in payload:
        return default
    value = payload[key]
    if not isinstance(value, bool):
        raise RuntimeError(f"{key} must be boolean")
    return value


def _optional_positive_int(payload: dict[str, Any], key: str) -> int | None:
    if key not in payload or payload[key] is None:
        return None
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"{key} must be a positive integer when supplied")
    return int(value)
