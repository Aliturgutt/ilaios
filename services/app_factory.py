"""Platform-side App Factory boundary for review-only client change requests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TypedDict

from services.app_design_quality import AppDesignAssessment


class AppFactoryError(PermissionError):
    """An app-factory request exceeds the bounded platform-side authority."""


_ALLOWED_PLATFORMS = frozenset({"windows", "android", "ios"})
_ALLOWED_ACTIONS = frozenset({"client_change_request", "build_plan", "test_plan"})
_FORBIDDEN_PATH_ROOTS = frozenset({"apps", "website", "web", "desktop", "mobile"})


class AppRequestProjection(TypedDict):
    request_id: str
    platform: str
    action: str
    objective: str
    request_sha256: str
    approved_for_review: bool
    approver: str
    client_mutated: bool


@dataclass(frozen=True, slots=True)
class AppRequest:
    request_id: str
    platform: str
    action: str
    objective: str
    target_path: str
    request_sha256: str
    approved_for_review: bool
    approver: str | None
    client_mutated: bool = False


class AppFactory:
    """Create platform-owned app requests without editing or deploying client surfaces."""

    def __init__(self) -> None:
        self._requests: dict[str, AppRequest] = {}

    @staticmethod
    def accept_design_quality(assessment: AppDesignAssessment) -> None:
        """Fail closed through the existing App Factory acceptance boundary."""
        if assessment.evaluator_id != "design.app-final-polish":
            raise ValueError("unrecognized app design quality evaluator")
        if assessment.status != "PASS" or assessment.blocking_findings:
            raise ValueError("app design quality gate failed")

    def propose(
        self,
        request_id: str,
        *,
        platform: str,
        action: str,
        objective: str,
        target_path: str,
    ) -> AppRequest:
        _require_id(request_id, "request_id")
        _require_text(objective, "objective")
        _require_path(target_path)
        if request_id in self._requests:
            raise AppFactoryError("request_id already exists")
        if platform not in _ALLOWED_PLATFORMS:
            raise AppFactoryError(f"unsupported app platform: {platform}")
        if action not in _ALLOWED_ACTIONS:
            raise AppFactoryError(f"unsupported app factory action: {action}")
        root = target_path.split("/", 1)[0].casefold()
        if root in _FORBIDDEN_PATH_ROOTS:
            raise AppFactoryError("client implementation paths are outside the platform boundary")

        canonical = json.dumps(
            {
                "action": action,
                "objective": objective.strip(),
                "platform": platform,
                "target_path": target_path,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        request = AppRequest(
            request_id=request_id,
            platform=platform,
            action=action,
            objective=objective.strip(),
            target_path=target_path,
            request_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            approved_for_review=False,
            approver=None,
        )
        self._requests[request_id] = request
        return request

    def approve_for_review(self, request_id: str, *, approver: str) -> AppRequest:
        _require_text(approver, "approver")
        request = self._requests.get(request_id)
        if request is None:
            raise AppFactoryError("app request does not exist")
        if request.approved_for_review:
            raise AppFactoryError("app request already approved for review")
        approved = AppRequest(
            request_id=request.request_id,
            platform=request.platform,
            action=request.action,
            objective=request.objective,
            target_path=request.target_path,
            request_sha256=request.request_sha256,
            approved_for_review=True,
            approver=approver.strip(),
        )
        self._requests[request_id] = approved
        return approved

    def review_projection(self, request_id: str) -> AppRequestProjection:
        request = self._requests.get(request_id)
        if request is None:
            raise AppFactoryError("app request does not exist")
        if not request.approved_for_review or request.approver is None:
            raise AppFactoryError("only approved app requests may project for review")
        return {
            "request_id": request.request_id,
            "platform": request.platform,
            "action": request.action,
            "objective": request.objective,
            "request_sha256": request.request_sha256,
            "approved_for_review": True,
            "approver": request.approver,
            "client_mutated": request.client_mutated,
        }

    def mutate_client(self, request_id: str) -> None:
        if request_id not in self._requests:
            raise AppFactoryError("app request does not exist")
        raise AppFactoryError("direct client implementation mutation is forbidden")

    def deploy_or_submit(self, request_id: str) -> None:
        if request_id not in self._requests:
            raise AppFactoryError("app request does not exist")
        raise AppFactoryError("deployment, signing and store submission are forbidden")


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise AppFactoryError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise AppFactoryError(f"{field} must be non-blank")


def _require_path(value: str) -> None:
    if not value or value != value.strip() or value.startswith("/") or ".." in value.split("/"):
        raise AppFactoryError("target_path must be a bounded relative path")
