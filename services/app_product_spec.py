"""Deterministic enterprise App Factory product-spec foundation.

This module is specification/planning only. It does not mutate client source, execute
builds, access secrets, deploy, sign, submit, or publish applications. Real
implementation remains downstream through the canonical ExecutionCoordinator,
Software Factory, Policy/Approval/Tool Gateway, validation and evidence boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, TypeVar


AppIntent = Literal["new", "revision", "reference", "migration"]
AppPlatform = Literal["windows", "android", "ios"]
CapabilityStatus = Literal[
    "AVAILABLE", "NEEDS_IMPLEMENTATION", "EXTERNAL_DEPENDENCY", "BLOCKED"
]
Complexity = Literal["small", "medium", "complex", "enterprise"]
RiskLevel = Literal["low", "medium", "high"]
Monetization = Literal[
    "free", "paid", "iap", "subscription", "physical-goods", "external-billing"
]

_T = TypeVar("_T", bound=str)


class AppProductSpecError(ValueError):
    """Enterprise App Factory specification input is invalid or ambiguous."""


@dataclass(frozen=True, slots=True)
class ProjectAdmission:
    project_id: str
    intent: AppIntent
    objective: str
    platforms: tuple[AppPlatform, ...]
    reference_asset_ids: tuple[str, ...]
    source_asset_id: str | None
    admission_sha256: str


@dataclass(frozen=True, slots=True)
class ProductSpec:
    project_id: str
    product_name: str
    objective: str
    platforms: tuple[AppPlatform, ...]
    actors: tuple[str, ...]
    screens: tuple[str, ...]
    capabilities: tuple[str, ...]
    locales: tuple[str, ...]
    accessibility_required: bool
    offline_required: bool
    monetization: Monetization
    spec_sha256: str


@dataclass(frozen=True, slots=True)
class CapabilityAssessment:
    capability: str
    status: CapabilityStatus
    reason: str


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    complexity: Complexity
    security: RiskLevel
    privacy: RiskLevel
    commerce: RiskLevel
    external_integration: RiskLevel
    store: RiskLevel
    assessment_sha256: str


def admit_project(
    *,
    project_id: str,
    intent: AppIntent,
    objective: str,
    platforms: tuple[AppPlatform, ...],
    reference_asset_ids: tuple[str, ...] = (),
    source_asset_id: str | None = None,
) -> ProjectAdmission:
    """Create an immutable admission record without granting implementation authority."""
    _require_token(project_id, "project_id")
    _require_text(objective, "objective")
    normalized_platforms = _normalize_unique(platforms, "platforms")
    if not normalized_platforms:
        raise AppProductSpecError("at least one target platform is required")
    normalized_refs = _normalize_unique(reference_asset_ids, "reference_asset_ids")
    if source_asset_id is not None:
        _require_token(source_asset_id, "source_asset_id")

    if intent in {"revision", "migration"} and source_asset_id is None:
        raise AppProductSpecError(f"{intent} intent requires an immutable source_asset_id")
    if intent == "reference" and not normalized_refs:
        raise AppProductSpecError("reference intent requires at least one reference asset")
    if intent == "new" and source_asset_id is not None:
        raise AppProductSpecError("new intent cannot include an existing source asset")

    canonical: dict[str, object] = {
        "intent": intent,
        "objective": objective.strip(),
        "platforms": list(normalized_platforms),
        "project_id": project_id,
        "reference_asset_ids": list(normalized_refs),
        "source_asset_id": source_asset_id,
    }
    return ProjectAdmission(
        project_id=project_id,
        intent=intent,
        objective=objective.strip(),
        platforms=normalized_platforms,
        reference_asset_ids=normalized_refs,
        source_asset_id=source_asset_id,
        admission_sha256=_sha256_json(canonical),
    )


def build_product_spec(
    *,
    admission: ProjectAdmission,
    product_name: str,
    actors: tuple[str, ...],
    screens: tuple[str, ...],
    capabilities: tuple[str, ...],
    locales: tuple[str, ...] = ("en",),
    accessibility_required: bool = True,
    offline_required: bool = False,
    monetization: Monetization = "free",
) -> ProductSpec:
    """Compile admitted product requirements into an immutable deterministic spec."""
    _require_token(product_name, "product_name")
    normalized_actors = _normalize_unique(actors, "actors")
    normalized_screens = _normalize_unique(screens, "screens")
    normalized_capabilities = _normalize_unique(capabilities, "capabilities")
    normalized_locales = _normalize_unique(locales, "locales")
    if not normalized_actors:
        raise AppProductSpecError("at least one actor is required")
    if not normalized_screens:
        raise AppProductSpecError("at least one screen is required")
    if not normalized_capabilities:
        raise AppProductSpecError("at least one capability is required")
    if not normalized_locales:
        raise AppProductSpecError("at least one locale is required")

    canonical: dict[str, object] = {
        "accessibility_required": accessibility_required,
        "actors": list(normalized_actors),
        "capabilities": list(normalized_capabilities),
        "locales": list(normalized_locales),
        "monetization": monetization,
        "objective": admission.objective,
        "offline_required": offline_required,
        "platforms": list(admission.platforms),
        "product_name": product_name,
        "project_id": admission.project_id,
        "screens": list(normalized_screens),
    }
    return ProductSpec(
        project_id=admission.project_id,
        product_name=product_name,
        objective=admission.objective,
        platforms=admission.platforms,
        actors=normalized_actors,
        screens=normalized_screens,
        capabilities=normalized_capabilities,
        locales=normalized_locales,
        accessibility_required=accessibility_required,
        offline_required=offline_required,
        monetization=monetization,
        spec_sha256=_sha256_json(canonical),
    )


def resolve_capabilities(
    spec: ProductSpec,
    *,
    available: frozenset[str] = frozenset(),
    external_dependencies: frozenset[str] = frozenset(),
    blocked: frozenset[str] = frozenset(),
) -> tuple[CapabilityAssessment, ...]:
    """Resolve capability maturity deterministically without inventing availability."""
    if available & external_dependencies or available & blocked or external_dependencies & blocked:
        raise AppProductSpecError("capability status sets must be mutually exclusive")

    assessments: list[CapabilityAssessment] = []
    for capability in spec.capabilities:
        if capability in blocked:
            status: CapabilityStatus = "BLOCKED"
            reason = "explicit prerequisite or policy blocker"
        elif capability in available:
            status = "AVAILABLE"
            reason = "capability is present in the supplied verified availability set"
        elif capability in external_dependencies:
            status = "EXTERNAL_DEPENDENCY"
            reason = "capability requires an external dependency or credential boundary"
        else:
            status = "NEEDS_IMPLEMENTATION"
            reason = "capability has no verified implementation in the supplied availability set"
        assessments.append(
            CapabilityAssessment(capability=capability, status=status, reason=reason)
        )
    return tuple(assessments)


def classify_risk(spec: ProductSpec) -> RiskAssessment:
    """Classify explicit spec signals; free-form objective text grants no capability."""
    capabilities = set(spec.capabilities)
    weighted_size = len(spec.screens) + len(spec.capabilities) + (2 * len(spec.platforms))
    if weighted_size >= 24 or len(spec.capabilities) >= 12:
        complexity: Complexity = "enterprise"
    elif weighted_size >= 16 or len(spec.capabilities) >= 8:
        complexity = "complex"
    elif weighted_size >= 8:
        complexity = "medium"
    else:
        complexity = "small"

    security = _risk_from_tokens(
        capabilities, {"authentication", "rbac", "admin", "secrets", "payments"}
    )
    privacy = _risk_from_tokens(
        capabilities, {"camera", "photos", "files", "tracking", "location", "biometrics"}
    )
    commerce: RiskLevel
    if spec.monetization in {"iap", "subscription", "external-billing"}:
        commerce = "high"
    elif spec.monetization == "paid":
        commerce = "medium"
    else:
        commerce = "low"
    external_integration = _risk_from_tokens(
        capabilities, {"integrations", "external-api", "webhooks", "payments"}
    )
    store: RiskLevel
    if "ios" in spec.platforms and "android" in spec.platforms:
        store = "high"
    elif any(platform in {"ios", "android"} for platform in spec.platforms):
        store = "medium"
    else:
        store = "low"

    canonical: dict[str, object] = {
        "commerce": commerce,
        "complexity": complexity,
        "external_integration": external_integration,
        "privacy": privacy,
        "security": security,
        "spec_sha256": spec.spec_sha256,
        "store": store,
    }
    return RiskAssessment(
        complexity=complexity,
        security=security,
        privacy=privacy,
        commerce=commerce,
        external_integration=external_integration,
        store=store,
        assessment_sha256=_sha256_json(canonical),
    )


def _risk_from_tokens(capabilities: set[str], sensitive: set[str]) -> RiskLevel:
    overlap = capabilities & sensitive
    if len(overlap) >= 2:
        return "high"
    if overlap:
        return "medium"
    return "low"


def _normalize_unique(values: tuple[_T, ...], field: str) -> tuple[_T, ...]:
    normalized: list[_T] = []
    seen: set[_T] = set()
    for value in values:
        _require_token(value, field)
        if value in seen:
            raise AppProductSpecError(f"{field} contains duplicate values")
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _require_token(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise AppProductSpecError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise AppProductSpecError(f"{field} must be non-blank")


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
