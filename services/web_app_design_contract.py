"""Deterministic Application Shell and Design System contracts for generated Web Apps.

This module turns a validated ``WebAppSpec`` plus optional reference-semantic evidence
into an auditable application-shell and design-system contract. It intentionally does
not render UI, choose a provider, mutate source, grant authority, or claim visual
fidelity. Exact screenshot fidelity requires explicit bounded measurements; when those
measurements are absent the contract stays truthfully marked as baseline-derived.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

from services.web_app_spec import WebAppSpec
from services.web_reference_semantics import WebReferenceSemanticBrief


class WebAppDesignContractError(ValueError):
    """A Web App design contract could not be derived safely."""


MeasurementSource = Literal["baseline", "reference-measurement"]

_ALLOWED_MEASUREMENT_KEYS = frozenset(
    {
        "spacing_scale_px",
        "font_size_scale_px",
        "line_height_scale",
        "font_weight_scale",
        "radius_scale_px",
        "table_row_height_px",
        "icon_size_scale_px",
        "sidebar_width_px",
        "topbar_height_px",
        "content_max_width_px",
        "grid_columns",
        "breakpoints_px",
    }
)

_BASELINE_MEASUREMENTS: dict[str, tuple[float, ...]] = {
    "spacing_scale_px": (4, 8, 12, 16, 24, 32, 48, 64),
    "font_size_scale_px": (12, 14, 16, 20, 24, 32, 40),
    "line_height_scale": (1.2, 1.35, 1.5, 1.65),
    "font_weight_scale": (400, 500, 600, 700),
    "radius_scale_px": (4, 8, 12, 16),
    "table_row_height_px": (44,),
    "icon_size_scale_px": (16, 20, 24),
    "sidebar_width_px": (240,),
    "topbar_height_px": (64,),
    "content_max_width_px": (1600,),
    "grid_columns": (12,),
    "breakpoints_px": (480, 768, 1024, 1280, 1536),
}

_SEMANTIC_STATUS_ROLES = (
    "info",
    "success",
    "warning",
    "danger",
    "neutral",
    "accent",
)

_COMPONENT_STATES = (
    "default",
    "hover",
    "focus-visible",
    "active",
    "selected",
    "disabled",
    "loading",
    "empty",
    "error",
)

_REQUIRED_SHELL_SLOTS = (
    "sidebar",
    "topbar",
    "project-switcher",
    "global-search",
    "notifications",
    "profile",
    "persistent-footer-status-bar",
    "nested-routes",
    "selected-navigation-state",
    "drawer-detail-panels",
)


@dataclass(frozen=True, slots=True)
class WebAppShellContract:
    shell_profile: str
    required_slots: tuple[str, ...]
    navigation_model: str
    route_model: str
    detail_surface_model: str
    responsive_navigation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WebDesignMeasurementSet:
    values: tuple[tuple[str, tuple[float, ...]], ...]
    source: MeasurementSource
    semantic_analysis_sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "values": {key: list(value) for key, value in self.values},
            "source": self.source,
            "semantic_analysis_sha256": self.semantic_analysis_sha256,
        }


@dataclass(frozen=True, slots=True)
class WebDesignSystemContract:
    measurements: WebDesignMeasurementSet
    semantic_status_roles: tuple[str, ...]
    component_states: tuple[str, ...]
    table_density: str
    responsive_strategy: str
    token_namespace: str
    reference_fidelity_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "measurements": self.measurements.to_dict(),
            "semantic_status_roles": list(self.semantic_status_roles),
            "component_states": list(self.component_states),
            "table_density": self.table_density,
            "responsive_strategy": self.responsive_strategy,
            "token_namespace": self.token_namespace,
            "reference_fidelity_status": self.reference_fidelity_status,
        }


@dataclass(frozen=True, slots=True)
class WebAppDesignContract:
    schema_version: str
    app_id: str
    app_spec_sha256: str
    semantic_analysis_sha256: str | None
    shell: WebAppShellContract
    design_system: WebDesignSystemContract
    acceptance_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "app_id": self.app_id,
            "app_spec_sha256": self.app_spec_sha256,
            "semantic_analysis_sha256": self.semantic_analysis_sha256,
            "shell": self.shell.to_dict(),
            "design_system": self.design_system.to_dict(),
            "acceptance_requirements": list(self.acceptance_requirements),
        }

    @property
    def contract_sha256(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def derive_web_app_design_contract(
    spec: WebAppSpec,
    *,
    semantic_brief: WebReferenceSemanticBrief | None = None,
    measurements: dict[str, tuple[float, ...]] | None = None,
) -> WebAppDesignContract:
    """Build an auditable shell/design contract without inventing measured fidelity."""
    semantic_sha = spec.reference_semantic_sha256
    if semantic_sha is None:
        if semantic_brief is not None:
            raise WebAppDesignContractError(
                "semantic brief was supplied but the WebAppSpec is not reference-bound"
            )
        if measurements is not None:
            raise WebAppDesignContractError(
                "reference measurements require a reference-bound WebAppSpec"
            )
    else:
        if semantic_brief is None:
            raise WebAppDesignContractError(
                "reference-bound WebAppSpec requires the exact semantic brief"
            )
        if semantic_brief.analysis_sha256 != semantic_sha:
            raise WebAppDesignContractError(
                "semantic brief digest does not match the WebAppSpec"
            )

    normalized_measurements, source = _measurements(measurements, semantic_sha)
    fidelity = (
        "MEASURED_REFERENCE_CONTRACT"
        if source == "reference-measurement"
        else "BASELINE_ONLY_NOT_REFERENCE_EXACT"
    )
    shell_profile = (
        "enterprise-dashboard"
        if spec.app_kind in {"dashboard", "admin"}
        else "enterprise-application"
    )
    shell = WebAppShellContract(
        shell_profile=shell_profile,
        required_slots=_REQUIRED_SHELL_SLOTS,
        navigation_model="persistent-primary-navigation-with-route-derived-selection",
        route_model="nested-routes-with-authenticated-layout-boundary",
        detail_surface_model="route-bound-drawer-or-detail-panel",
        responsive_navigation="persistent-wide-collapsible-compact",
    )
    design_system = WebDesignSystemContract(
        measurements=normalized_measurements,
        semantic_status_roles=_SEMANTIC_STATUS_ROLES,
        component_states=_COMPONENT_STATES,
        table_density="dense-enterprise-with-accessible-targets",
        responsive_strategy="mobile-first-explicit-breakpoint-contract",
        token_namespace=f"ilaios.webapp.{spec.app_id}",
        reference_fidelity_status=fidelity,
    )
    acceptance = (
        "all required application-shell slots render on authenticated application routes",
        "selected navigation state is derived from the active nested route",
        "drawer/detail panels preserve keyboard focus and route/back behavior",
        "spacing typography radius table icon layout and breakpoint values come only from the deterministic token contract",
        "component variants cover default hover focus active selected disabled loading empty and error states",
        "semantic status colors are role-based and preserve accessible contrast",
        "compact navigation and table/detail behavior are verified at every declared breakpoint",
        (
            "measured reference values are bound to the exact semantic-analysis digest"
            if source == "reference-measurement"
            else "reference-exact fidelity remains unproven until bounded measurements are supplied"
        ),
    )
    return WebAppDesignContract(
        schema_version="ilaios.web-app-design-contract.v1",
        app_id=spec.app_id,
        app_spec_sha256=spec.spec_sha256,
        semantic_analysis_sha256=semantic_sha,
        shell=shell,
        design_system=design_system,
        acceptance_requirements=acceptance,
    )


def _measurements(
    supplied: dict[str, tuple[float, ...]] | None,
    semantic_sha: str | None,
) -> tuple[WebDesignMeasurementSet, MeasurementSource]:
    if supplied is None:
        values = tuple(sorted(_BASELINE_MEASUREMENTS.items()))
        result = WebDesignMeasurementSet(
            values=values,
            source="baseline",
            semantic_analysis_sha256=None,
        )
        return result, "baseline"
    unknown = set(supplied).difference(_ALLOWED_MEASUREMENT_KEYS)
    missing = _ALLOWED_MEASUREMENT_KEYS.difference(supplied)
    if unknown:
        raise WebAppDesignContractError(
            "unsupported design measurement keys: " + ", ".join(sorted(unknown))
        )
    if missing:
        raise WebAppDesignContractError(
            "reference measurement set is incomplete: " + ", ".join(sorted(missing))
        )
    validated: list[tuple[str, tuple[float, ...]]] = []
    for key in sorted(_ALLOWED_MEASUREMENT_KEYS):
        raw = supplied[key]
        if not isinstance(raw, tuple) or not raw:
            raise WebAppDesignContractError(f"design measurement {key} must be a non-empty tuple")
        numbers: list[float] = []
        for item in raw:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise WebAppDesignContractError(f"design measurement {key} is non-numeric")
            number = float(item)
            if number <= 0 or number > 4096:
                raise WebAppDesignContractError(f"design measurement {key} is out of bounds")
            numbers.append(number)
        if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
            raise WebAppDesignContractError(
                f"design measurement {key} must be strictly increasing"
            )
        validated.append((key, tuple(numbers)))
    result = WebDesignMeasurementSet(
        values=tuple(validated),
        source="reference-measurement",
        semantic_analysis_sha256=semantic_sha,
    )
    return result, "reference-measurement"
