"""Deterministic Stage-2 application-architecture planning contracts.

This module is planning/specification only. It cannot mutate source, execute builds,
access credentials, deploy, sign, submit, publish, or create a second runtime/core.
Implementation remains downstream through the canonical ExecutionCoordinator,
Software Factory, Policy/Approval/Tool Gateway, validation and evidence boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from services.app_product_spec import (
    CapabilityAssessment,
    ProductSpec,
    RiskAssessment,
)


ArchitectureTier = Literal["simple", "service-backed", "enterprise"]
PersistenceMode = Literal["none", "relational"]
RealtimeMode = Literal["none", "event-stream"]
FileMode = Literal["none", "object-storage"]
NativeMode = Literal["none", "mobile-capability-pack"]


class AppArchitecturePlanError(ValueError):
    """Architecture planning input is invalid, ambiguous, or blocked."""


@dataclass(frozen=True, slots=True)
class ApplicationArchitecturePlan:
    project_id: str
    spec_sha256: str
    architecture_tier: ArchitectureTier
    persistence_mode: PersistenceMode
    realtime_mode: RealtimeMode
    file_mode: FileMode
    native_mode: NativeMode
    requires_backend_api: bool
    requires_authentication: bool
    requires_authorization: bool
    requires_migrations: bool
    requires_external_integrations: bool
    requires_commerce_runtime: bool
    implementation_authority: Literal["software-factory"]
    direct_publication_allowed: Literal[False]
    plan_sha256: str


def plan_application_architecture(
    *,
    spec: ProductSpec,
    capability_assessments: tuple[CapabilityAssessment, ...],
    risk: RiskAssessment,
) -> ApplicationArchitecturePlan:
    """Compile a deterministic product architecture plan without execution authority."""
    if not capability_assessments:
        raise AppArchitecturePlanError("capability assessments are required")

    assessed_capabilities = tuple(item.capability for item in capability_assessments)
    if assessed_capabilities != spec.capabilities:
        raise AppArchitecturePlanError(
            "capability assessments must match ProductSpec capabilities and ordering"
        )
    if any(item.status == "BLOCKED" for item in capability_assessments):
        raise AppArchitecturePlanError("blocked capabilities prevent architecture planning")

    capabilities = set(spec.capabilities)
    requires_authentication = bool(
        capabilities & {"authentication", "oauth", "mfa", "account"}
    )
    requires_authorization = bool(
        capabilities & {"rbac", "permissions", "admin", "project-access"}
    )
    requires_persistence = bool(
        capabilities
        & {
            "database",
            "persistence",
            "crud",
            "accounts",
            "workflows",
            "projects",
            "history",
        }
    )
    requires_realtime = bool(
        capabilities & {"realtime", "websocket", "sse", "notifications"}
    )
    requires_files = bool(capabilities & {"files", "uploads", "media", "outputs"})
    requires_native = any(platform in {"android", "ios"} for platform in spec.platforms)
    requires_external_integrations = bool(
        capabilities & {"integrations", "external-api", "webhooks", "payments"}
    )
    requires_commerce_runtime = spec.monetization in {
        "paid",
        "iap",
        "subscription",
        "external-billing",
    }

    requires_backend_api = any(
        (
            requires_authentication,
            requires_authorization,
            requires_persistence,
            requires_realtime,
            requires_files,
            requires_external_integrations,
            requires_commerce_runtime,
        )
    )
    requires_migrations = requires_persistence

    architecture_tier: ArchitectureTier
    if risk.complexity == "enterprise" or any(
        level == "high"
        for level in (
            risk.security,
            risk.privacy,
            risk.commerce,
            risk.external_integration,
            risk.store,
        )
    ):
        architecture_tier = "enterprise"
    elif requires_backend_api:
        architecture_tier = "service-backed"
    else:
        architecture_tier = "simple"

    persistence_mode: PersistenceMode = "relational" if requires_persistence else "none"
    realtime_mode: RealtimeMode = "event-stream" if requires_realtime else "none"
    file_mode: FileMode = "object-storage" if requires_files else "none"
    native_mode: NativeMode = "mobile-capability-pack" if requires_native else "none"

    canonical: dict[str, object] = {
        "architecture_tier": architecture_tier,
        "direct_publication_allowed": False,
        "file_mode": file_mode,
        "implementation_authority": "software-factory",
        "native_mode": native_mode,
        "persistence_mode": persistence_mode,
        "project_id": spec.project_id,
        "realtime_mode": realtime_mode,
        "requires_authentication": requires_authentication,
        "requires_authorization": requires_authorization,
        "requires_backend_api": requires_backend_api,
        "requires_commerce_runtime": requires_commerce_runtime,
        "requires_external_integrations": requires_external_integrations,
        "requires_migrations": requires_migrations,
        "spec_sha256": spec.spec_sha256,
    }
    return ApplicationArchitecturePlan(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        architecture_tier=architecture_tier,
        persistence_mode=persistence_mode,
        realtime_mode=realtime_mode,
        file_mode=file_mode,
        native_mode=native_mode,
        requires_backend_api=requires_backend_api,
        requires_authentication=requires_authentication,
        requires_authorization=requires_authorization,
        requires_migrations=requires_migrations,
        requires_external_integrations=requires_external_integrations,
        requires_commerce_runtime=requires_commerce_runtime,
        implementation_authority="software-factory",
        direct_publication_allowed=False,
        plan_sha256=_sha256_json(canonical),
    )


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
