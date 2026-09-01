from __future__ import annotations

from pathlib import Path

import pytest

from services.runtime.security_agent_adapters import (
    WEB_API_ADAPTER_KIND,
    SecurityAgentAdapterError,
    SecurityAgentRuntimeAdapters,
)
from services.security_auth_authorization_analysis import (
    AuthAuthorizationCaseKind,
    AuthAuthorizationObservation,
    analyze_auth_authorization_observations,
)
from services.security_methodology_skills import AUTH_AUTHORIZATION_TESTING_SKILL_ID


def _obs(
    case_id: str,
    kind: AuthAuthorizationCaseKind,
    status_code: int,
) -> AuthAuthorizationObservation:
    return AuthAuthorizationObservation(case_id, kind, status_code)


def test_auth_authorization_happy_path_has_no_findings() -> None:
    report = analyze_auth_authorization_observations(
        "authz",
        (
            _obs("anon", AuthAuthorizationCaseKind.UNAUTHENTICATED, 401),
            _obs("tenant", AuthAuthorizationCaseKind.CROSS_TENANT, 403),
            _obs("role", AuthAuthorizationCaseKind.INSUFFICIENT_ROLE, 403),
            _obs("allowed", AuthAuthorizationCaseKind.AUTHORIZED, 200),
        ),
    )
    assert report.findings == ()
    assert report.passed is True


def test_auth_authorization_detects_bypass_and_regression() -> None:
    report = analyze_auth_authorization_observations(
        "authz",
        (
            _obs("anon", AuthAuthorizationCaseKind.UNAUTHENTICATED, 200),
            _obs("tenant", AuthAuthorizationCaseKind.CROSS_TENANT, 200),
            _obs("role", AuthAuthorizationCaseKind.INSUFFICIENT_ROLE, 302),
            _obs("allowed", AuthAuthorizationCaseKind.AUTHORIZED, 403),
        ),
    )
    ids = {item.finding_id for item in report.findings}
    assert ids == {
        "AUTH-UNAUTHENTICATED-NOT-DENIED",
        "AUTH-CROSS-TENANT-NOT-DENIED",
        "AUTH-INSUFFICIENT-ROLE-NOT-DENIED",
        "AUTH-AUTHORIZED-FLOW-FAILED",
    }
    assert report.passed is False
    cross_tenant = next(
        item for item in report.findings
        if item.finding_id == "AUTH-CROSS-TENANT-NOT-DENIED"
    )
    assert cross_tenant.severity.name == "CRITICAL"


def test_auth_authorization_rejects_invalid_or_duplicate_evidence() -> None:
    with pytest.raises(ValueError, match="valid HTTP status"):
        _obs("bad", AuthAuthorizationCaseKind.UNAUTHENTICATED, 99)

    duplicate = _obs("same", AuthAuthorizationCaseKind.UNAUTHENTICATED, 401)
    with pytest.raises(ValueError, match="unique"):
        analyze_auth_authorization_observations("authz", (duplicate, duplicate))

    with pytest.raises(ValueError, match="at least one"):
        analyze_auth_authorization_observations("authz", ())


def _runtime_payload(repository_root: Path) -> dict[str, object]:
    return {
        "scope_id": "authz-runtime",
        "repository_root": str(repository_root),
        "_ilaios_skill": {"skill_id": AUTH_AUTHORIZATION_TESTING_SKILL_ID},
        "observations": [
            {"case_id": "anon", "kind": "unauthenticated", "status_code": 401},
            {"case_id": "tenant", "kind": "cross_tenant", "status_code": 403},
            {
                "case_id": "role",
                "kind": "insufficient_role",
                "status_code": 403,
            },
            {"case_id": "allowed", "kind": "authorized", "status_code": 200},
        ],
    }


def test_auth_authorization_skill_routes_through_existing_web_api_adapter(
    tmp_path: Path,
) -> None:
    adapter = SecurityAgentRuntimeAdapters().runtime_adapters()[WEB_API_ADAPTER_KIND]
    output = adapter(_runtime_payload(tmp_path))
    assert output["scope_id"] == "authz-runtime"
    assert output["passed"] is True
    assert output["finding_count"] == 0


def test_auth_authorization_runtime_fails_closed_on_malformed_observation(
    tmp_path: Path,
) -> None:
    adapter = SecurityAgentRuntimeAdapters().runtime_adapters()[WEB_API_ADAPTER_KIND]
    payload = _runtime_payload(tmp_path)
    payload["observations"] = [
        {"case_id": "tenant", "kind": "cross_tenant", "status_code": "200"}
    ]
    with pytest.raises(SecurityAgentAdapterError, match="failed closed"):
        adapter(payload)
