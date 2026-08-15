"""Bounded deterministic repair policy for Web Factory generation defects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace

from .web_factory import WebsiteSpec


class WebRepairError(RuntimeError):
    """Raised when a Web Factory defect cannot be repaired safely and deterministically."""


@dataclass(frozen=True, slots=True)
class WebRepairAttempt:
    attempt: int
    category: str
    reason: str
    before_spec_hash: str
    after_spec_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt": self.attempt,
            "category": self.category,
            "reason": self.reason,
            "before_spec_hash": self.before_spec_hash,
            "after_spec_hash": self.after_spec_hash,
        }


class BoundedWebRepairPolicy:
    """Allow at most one deterministic structural repair, then fail closed."""

    max_attempts = 1

    def repair_spec(
        self,
        spec: WebsiteSpec,
        error: ValueError,
        *,
        prior_attempts: int,
    ) -> tuple[WebsiteSpec, WebRepairAttempt]:
        if prior_attempts >= self.max_attempts:
            raise WebRepairError("web repair budget exhausted") from error

        message = str(error).casefold()
        if not any(
            marker in message
            for marker in (
                "pages must be non-empty and unique",
                "requires home and contact routes",
                "locales must be en/tr",
            )
        ):
            raise WebRepairError("web defect is outside the deterministic repair policy") from error

        pages = tuple(dict.fromkeys(spec.pages))
        pages = tuple(page for page in pages if page not in {"home", "contact"})
        pages = ("home", *pages, "contact")
        locales = tuple(locale for locale in dict.fromkeys(spec.locales) if locale in {"en", "tr"})
        if not locales:
            locales = ("en",)

        repaired = replace(spec, pages=pages, locales=locales)
        before_hash = _spec_hash(spec)
        after_hash = _spec_hash(repaired)
        if before_hash == after_hash:
            raise WebRepairError("recognized web defect produced no safe repair") from error

        category = "requirements-structure"
        if "locales" in message:
            category = "localization-structure"
        attempt = WebRepairAttempt(
            attempt=prior_attempts + 1,
            category=category,
            reason="deterministic WebsiteSpec normalization",
            before_spec_hash=before_hash,
            after_spec_hash=after_hash,
        )
        return repaired, attempt


def _spec_hash(spec: WebsiteSpec) -> str:
    payload = json.dumps(
        asdict(spec),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
