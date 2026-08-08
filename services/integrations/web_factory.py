"""Governed deterministic Web Factory golden workflow."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from services.runtime import ExecutionGrant, GrantPolicy


@dataclass(frozen=True, slots=True)
class WebsiteAcceptance:
    manifest_version: str
    site_id: str
    artifact_hash: str
    required_pages: tuple[str, ...]
    official_brand: str
    accepted: bool


class GovernedWebFactory:
    def __init__(self, grants: GrantPolicy) -> None:
        self._grants = grants

    def build_official_site(
        self,
        site_id: str,
        pages: tuple[str, ...],
        *,
        grant: ExecutionGrant,
        now: datetime,
    ) -> WebsiteAcceptance:
        self._grants.authorize(
            grant,
            subject_id=grant.subject_id,
            action="web.build",
            resource=site_id,
            now=now,
        )
        required = ("home", "product", "security", "contact")
        if tuple(sorted(set(pages))) != tuple(sorted(required)):
            raise ValueError("official website requires the canonical page set")
        payload = json.dumps(
            {"brand": "ILAIOS", "pages": required, "site_id": site_id},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        self._grants.record_side_effect(grant, site_id)
        return WebsiteAcceptance(
            "1.0", site_id, hashlib.sha256(payload).hexdigest(), required, "ILAIOS", True
        )
