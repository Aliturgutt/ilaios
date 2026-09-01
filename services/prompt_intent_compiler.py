"""Platform-wide prompt admission compiler for governed ILAIOS execution.

The compiler is an advisory admission layer, not a second execution router. It
normalizes novice input, derives canonical capability hints, detects only true
alternative ambiguity, and emits an objective the existing governed execution
coordinator can classify. It never grants execution authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class PromptDomain(str, Enum):
    WEB = "web"
    VIDEO = "video"
    APP = "app"
    SOFTWARE = "software"
    RESEARCH = "research"
    DOCUMENT = "document"
    COMMERCE = "commerce"
    PERSONAL = "personal"
    SECURITY = "security"
    BUSINESS = "business"
    GENERAL = "general"


class PromptRisk(str, Enum):
    STANDARD = "standard"
    ELEVATED = "elevated"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class PromptCompilation:
    raw_objective: str
    normalized_objective: str
    domain: PromptDomain
    domains: tuple[PromptDomain, ...]
    intent: str
    output_type: str
    constraints: tuple[str, ...]
    suggested_capabilities: tuple[str, ...]
    success_criteria: tuple[str, ...]
    missing_critical_information: tuple[str, ...]
    ambiguity_reasons: tuple[str, ...]
    risk: PromptRisk
    clarification_questions: tuple[str, ...]
    canonical_objective: str

    @property
    def needs_clarification(self) -> bool:
        return bool(self.missing_critical_information or self.ambiguity_reasons)

    @property
    def is_multi_domain(self) -> bool:
        return len(self.domains) > 1


_DOMAIN_TERMS: dict[PromptDomain, tuple[str, ...]] = {
    PromptDomain.VIDEO: (
        "video",
        "mp4",
        "reel",
        "reels",
        "short video",
        "tanıtım videosu",
        "tanitim videosu",
        "youtube video",
        "tiktok video",
        "animasyon",
        "animation",
        "klip",
        "clip",
    ),
    PromptDomain.WEB: (
        "website",
        "web site",
        "web sitesi",
        "sitesi",
        "site yap",
        "siteyi",
        "landing page",
        "internet sitesi",
        "homepage",
        "web app",
        "web application",
        "web uygulaması",
        "web uygulamasi",
        "dashboard",
        "admin panel",
        "management dashboard",
        "yönetim paneli",
        "yonetim paneli",
        "customer portal",
        "client portal",
        "müşteri portalı",
        "musteri portali",
    ),
    PromptDomain.APP: (
        "mobile app",
        "mobil uygulama",
        "desktop app",
        "masaustu uygulama",
        "masaüstü uygulama",
        "windows app",
        "ios app",
        "android app",
        "iphone app",
        "mac app",
        "macos app",
    ),
    PromptDomain.SOFTWARE: (
        "software",
        "yazılım",
        "yazilim",
        "codebase",
        "repository",
        "repo",
        "api",
        "backend",
        "frontend",
        "program",
    ),
    PromptDomain.RESEARCH: (
        "research",
        "araştır",
        "arastir",
        "dataset",
        "veri analizi",
        "data analysis",
        "analiz et",
        "analyze",
    ),
    PromptDomain.DOCUMENT: (
        "document",
        "dokuman",
        "doküman",
        "pdf",
        "write a report",
        "rapor hazırla",
        "rapor hazirla",
    ),
    PromptDomain.COMMERCE: (
        "campaign",
        "kampanya",
        "marketing",
        "pazarlama",
        "sales plan",
        "satış planı",
        "satis plani",
    ),
    PromptDomain.PERSONAL: (
        "calendar",
        "takvim",
        "reminder",
        "hatirlatici",
        "hatırlatıcı",
        "checklist",
    ),
    PromptDomain.SECURITY: (
        "security review",
        "guvenlik",
        "güvenlik",
        "sast",
        "threat model",
        "secret scan",
        "security scan",
    ),
    PromptDomain.BUSINESS: (
        "finance",
        "finans",
        "operations",
        "operasyon",
        "strategy",
        "strateji",
        "executive",
        "yönetim analizi",
        "yonetim analizi",
    ),
}

_CAPABILITY_IDS: dict[PromptDomain, str] = {
    PromptDomain.VIDEO: "ilaios.capability.video-media-factory",
    PromptDomain.WEB: "ilaios.capability.web-factory",
    PromptDomain.APP: "ilaios.capability.app-factory",
    PromptDomain.SOFTWARE: "ilaios.capability.software-factory",
    PromptDomain.RESEARCH: "ilaios.capability.research-data",
    PromptDomain.DOCUMENT: "ilaios.capability.creative-document",
    PromptDomain.COMMERCE: "ilaios.capability.commerce-growth",
    PromptDomain.PERSONAL: "ilaios.capability.personal-operations",
    PromptDomain.SECURITY: "ilaios.capability.security-factory",
}

_CANONICAL_HINTS: dict[PromptDomain, str] = {
    PromptDomain.VIDEO: "video",
    PromptDomain.WEB: "website",
    PromptDomain.APP: "mobile app",
    PromptDomain.SOFTWARE: "software",
    PromptDomain.RESEARCH: "research",
    PromptDomain.DOCUMENT: "document",
    PromptDomain.COMMERCE: "marketing",
    PromptDomain.PERSONAL: "calendar",
    PromptDomain.SECURITY: "security review",
    PromptDomain.BUSINESS: "business workflow",
}

_HIGH_RISK_TERMS = (
    "publish",
    "yayınla",
    "production deploy",
    "deploy to production",
    "external mutation",
    "ödeme",
    "odeme",
    "payment",
    "send email",
    "email gönder",
    "email gonder",
    "private data",
    "personal data",
    "sensitive data",
    "kişisel veri",
    "kisisel veri",
    "password",
    "secret",
    "api key",
    "token",
    "credit card",
    "kredi kart",
)

_ELEVATED_RISK_TERMS = (
    "deploy",
    "post et",
    "paylaş",
    "share publicly",
    "external",
    "müşteriye gönder",
    "send to customer",
)

_DURATION_RE = re.compile(
    r"\b(\d{1,4})\s*(?:saniye|seconds?|secs?|sn)\b",
    re.IGNORECASE,
)
_ALTERNATIVE_RE = re.compile(r"\b(?:or|veya|ya\s+da)\b", re.IGNORECASE)


def compile_prompt(objective: str) -> PromptCompilation:
    """Compile raw input into a provider-neutral, governed admission record."""
    if not objective or objective != objective.strip():
        raise ValueError("prompt objective must be non-blank and trimmed")
    if len(objective) > 20_000:
        raise ValueError("prompt objective exceeds one-prompt input limit")

    normalized = " ".join(objective.split())
    folded = normalized.casefold()
    domains = tuple(
        domain
        for domain, terms in _DOMAIN_TERMS.items()
        if any(term in folded for term in terms)
    )
    ambiguity: list[str] = []
    missing: list[str] = []
    questions: list[str] = []

    if len(domains) > 1 and _ALTERNATIVE_RE.search(folded):
        ambiguity.append("multiple alternative execution domains were requested")
        missing.append("target execution domain")
        questions.append(
            "Bu alternatiflerden hangisi ana çıktı olmalı: "
            + ", ".join(domain.value for domain in domains)
            + "?"
        )

    if len(domains) == 1:
        domain = domains[0]
        intent, output_type = _intent_and_output(domain)
    elif len(domains) > 1:
        domain = PromptDomain.GENERAL
        intent, output_type = "multi_capability_goal", "multi_result"
    else:
        domain = PromptDomain.GENERAL
        intent, output_type = "fulfill_user_goal", "general_result"

    risk = _risk(folded)
    constraints = _constraints(normalized, folded)
    suggested_capabilities = tuple(
        _CAPABILITY_IDS[item] for item in domains if item in _CAPABILITY_IDS
    )
    success_criteria = _success_criteria(domains)
    canonical = _canonical_objective(domains, normalized)

    return PromptCompilation(
        raw_objective=objective,
        normalized_objective=normalized,
        domain=domain,
        domains=domains,
        intent=intent,
        output_type=output_type,
        constraints=constraints,
        suggested_capabilities=suggested_capabilities,
        success_criteria=success_criteria,
        missing_critical_information=tuple(missing),
        ambiguity_reasons=tuple(ambiguity),
        risk=risk,
        clarification_questions=tuple(questions),
        canonical_objective=canonical,
    )


def _risk(folded: str) -> PromptRisk:
    if any(term in folded for term in _HIGH_RISK_TERMS):
        return PromptRisk.HIGH
    if any(term in folded for term in _ELEVATED_RISK_TERMS):
        return PromptRisk.ELEVATED
    return PromptRisk.STANDARD


def _constraints(normalized: str, folded: str) -> tuple[str, ...]:
    constraints: list[str] = []
    duration = _DURATION_RE.search(normalized)
    if duration:
        constraints.append(f"duration_seconds={int(duration.group(1))}")
    if any(term in folded for term in ("türkçe", "turkish", "turkce")):
        constraints.append("locale=tr")
    if any(term in folded for term in ("english", "ingilizce")):
        constraints.append("locale=en")
    if any(
        term in folded for term in ("responsive", "mobil uyumlu", "mobile friendly")
    ):
        constraints.append("responsive=true")
    return tuple(constraints)


def _intent_and_output(domain: PromptDomain) -> tuple[str, str]:
    return {
        PromptDomain.WEB: ("build_finished_product", "website"),
        PromptDomain.VIDEO: ("build_finished_product", "video"),
        PromptDomain.APP: ("build_finished_product", "app"),
        PromptDomain.SOFTWARE: ("build_finished_product", "software"),
        PromptDomain.RESEARCH: ("produce_research_outcome", "research_result"),
        PromptDomain.DOCUMENT: ("produce_document", "document"),
        PromptDomain.COMMERCE: ("produce_commerce_outcome", "commerce_result"),
        PromptDomain.PERSONAL: ("perform_personal_operation", "personal_result"),
        PromptDomain.SECURITY: ("perform_security_review", "security_result"),
        PromptDomain.BUSINESS: ("produce_business_outcome", "business_result"),
        PromptDomain.GENERAL: ("fulfill_user_goal", "general_result"),
    }[domain]


def _success_criteria(domains: tuple[PromptDomain, ...]) -> tuple[str, ...]:
    if not domains:
        return ("user objective is fulfilled",)
    criteria = [
        "requested outcome is produced",
        "existing governance and approval requirements remain authoritative",
        "validation result is recorded before completion",
    ]
    if any(
        domain
        in {
            PromptDomain.WEB,
            PromptDomain.VIDEO,
            PromptDomain.APP,
            PromptDomain.SOFTWARE,
        }
        for domain in domains
    ):
        criteria.append("finished-product evidence is available")
    if len(domains) > 1:
        criteria.append("every requested capability reaches a valid terminal state")
    return tuple(criteria)


def _canonical_objective(domains: tuple[PromptDomain, ...], normalized: str) -> str:
    if not domains:
        return normalized
    hints = tuple(_CANONICAL_HINTS[domain] for domain in domains)
    folded = normalized.casefold()
    if all(hint in folded for hint in hints):
        return normalized
    if len(hints) == 1:
        return f"{hints[0]} task: {normalized}"
    return f"{' '.join(hints)} task: {normalized}"
