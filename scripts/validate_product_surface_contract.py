from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "product_surface_contract.json"

REQUIRED_FEATURE_FIELDS = {
    "feature_id",
    "canonical_name",
    "canonical_source",
    "category",
    "maturity",
    "availability",
    "public_visibility",
    "website_projection",
    "desktop_projection",
    "runtime_required",
    "evidence_required",
    "authority_owner",
    "locale_requirements",
    "security_classification",
}
PROTECTED_BOUNDARIES = {
    "policy",
    "approval",
    "tool-gateway",
    "validation",
    "audit-evidence",
    "tenant-security",
}
ALLOWED_WEBSITE = {"required", "not-applicable"}
ALLOWED_DESKTOP = {"runtime-derived", "explanatory-only", "not-applicable"}


class ContractError(ValueError):
    pass


def _derived(value: object, field: str) -> None:
    if not isinstance(value, dict) or value.get("mode") != "derived" or not value.get("source"):
        raise ContractError(f"{field} must be derived from an explicit canonical source")


def validate_contract(data: dict[str, object], *, root: Path = ROOT) -> None:
    if data.get("schema_version") != 1:
        raise ContractError("unsupported schema_version")

    authority = data.get("authority_model")
    if not isinstance(authority, dict):
        raise ContractError("authority_model is required")
    if authority.get("owner") != "canonical-control-plane" or authority.get("surface_authority") is not False:
        raise ContractError("surfaces must not become runtime authority")
    boundaries = set(authority.get("protected_boundaries", []))
    if boundaries != PROTECTED_BOUNDARIES:
        raise ContractError("protected authority boundaries must be complete and exact")

    for source_field in ("maturity_source", "registry_source"):
        source = data.get(source_field)
        if not isinstance(source, str) or not (root / source).is_file():
            raise ContractError(f"missing canonical source: {source_field}={source!r}")

    surfaces = data.get("surfaces")
    if not isinstance(surfaces, dict):
        raise ContractError("surfaces are required")
    website = surfaces.get("website")
    desktop = surfaces.get("desktop")
    if not isinstance(website, dict) or not isinstance(desktop, dict):
        raise ContractError("website and desktop projections are required")
    if website.get("may_assert_runtime_state") is not False or desktop.get("may_assert_runtime_state") is not False:
        raise ContractError("UI surfaces cannot assert authoritative runtime state")
    if website.get("locales") != ["en", "tr"] or website.get("semantic_locale_parity_required") is not True:
        raise ContractError("website EN/TR semantic parity must be fail-closed")
    if desktop.get("authoritative_runtime_source") != "control-plane" or desktop.get("stale_state_policy") != "fail-closed":
        raise ContractError("desktop must derive runtime truth from control-plane and fail closed on stale state")

    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise ContractError("features must be a non-empty list")

    seen: set[str] = set()
    for feature in features:
        if not isinstance(feature, dict):
            raise ContractError("feature entries must be objects")
        missing = REQUIRED_FEATURE_FIELDS - set(feature)
        if missing:
            raise ContractError(f"missing feature fields: {sorted(missing)}")
        feature_id = feature["feature_id"]
        if not isinstance(feature_id, str) or not feature_id:
            raise ContractError("feature_id must be non-empty")
        if feature_id in seen:
            raise ContractError(f"duplicate feature_id: {feature_id}")
        seen.add(feature_id)

        source = feature["canonical_source"]
        if not isinstance(source, str) or not (root / source).is_file():
            raise ContractError(f"stale or missing canonical_source for {feature_id}: {source!r}")
        _derived(feature["maturity"], f"{feature_id}.maturity")
        _derived(feature["availability"], f"{feature_id}.availability")
        if feature["authority_owner"] != "canonical-control-plane":
            raise ContractError(f"authority violation: {feature_id}")
        if feature["locale_requirements"] != ["en", "tr"]:
            raise ContractError(f"locale parity violation: {feature_id}")
        if feature["website_projection"] not in ALLOWED_WEBSITE:
            raise ContractError(f"invalid website projection: {feature_id}")
        if feature["desktop_projection"] not in ALLOWED_DESKTOP:
            raise ContractError(f"invalid desktop projection: {feature_id}")
        if feature["evidence_required"] is not True:
            raise ContractError(f"evidence must be required: {feature_id}")


def main() -> int:
    try:
        data = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ContractError("contract root must be an object")
        validate_contract(data)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"PRODUCT SURFACE PARITY: FAIL: {exc}", file=sys.stderr)
        return 1
    print("PRODUCT SURFACE PARITY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
