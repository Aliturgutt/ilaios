"""Structured Web/App requirements derived from one bounded user objective.

This module extends Web Factory requirements modeling without replacing the existing
``WebsiteSpec`` path. It describes dashboard/application needs (auth, data, CRUD,
tables, charts, external APIs, realtime, booking, commerce) separately from runtime
readiness. A requirement being present in ``WebAppSpec`` is not evidence that an
implementation adapter exists or that the capability is production-ready.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Literal

from services.web_reference_semantics import WebReferenceSemanticBrief

_MAX_OBJECTIVE_CHARS = 20_000
_MAX_RESOURCES = 12
_WEB_APP_TERMS = (
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
)
_NON_WEB_PLATFORM_TERMS = (
    "mobile app",
    "android app",
    "ios app",
    "iphone app",
    "desktop app",
    "windows app",
    "mac app",
    "macos app",
    "mobil uygulama",
    "masaüstü uygulama",
    "masaustu uygulama",
)
_RESOURCE_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("users", ("users", "user management", "kullanıcılar", "kullanici", "üyeler", "uyeler")),
    ("projects", ("projects", "project management", "projeler", "proje yönet", "proje yonet")),
    ("tasks", ("tasks", "task management", "görevler", "gorevler", "işler", "isler")),
    ("orders", ("orders", "order management", "sipariş", "siparis")),
    ("products", ("products", "product catalog", "ürünler", "urunler", "katalog")),
    ("customers", ("customers", "clients", "müşteriler", "musteriler")),
    ("bookings", ("bookings", "reservations", "appointments", "rezervasyon", "randevu")),
    ("invoices", ("invoices", "billing records", "faturalar", "fatura")),
    ("tickets", ("tickets", "support tickets", "destek talepleri", "destek kayıt", "destek kayit")),
    (
        "documents",
        (
            "documents",
            "document management",
            "files",
            "dokümanlar",
            "dokumanlar",
            "belgeler",
        ),
    ),
)
_CRUD_TERMS = (
    "crud",
    "create edit delete",
    "create, edit, delete",
    "create update delete",
    "manage records",
    "record management",
    "ekle düzenle sil",
    "ekle duzenle sil",
    "oluştur güncelle sil",
    "olustur guncelle sil",
    "yönetebil",
    "yonetebil",
)
_AUTH_TERMS = (
    "auth",
    "authentication",
    "login",
    "sign in",
    "user account",
    "role based",
    "rbac",
    "giriş",
    "giris",
    "oturum",
    "kullanıcı hesab",
    "kullanici hesab",
    "rol bazlı",
    "rol bazli",
)
_TABLE_TERMS = ("table", "data grid", "list view", "tablo", "liste")
_CHART_TERMS = ("chart", "graph", "analytics", "metrics", "grafik", "analitik", "metrik")
_EXTERNAL_API_TERMS = (
    "external api",
    "third-party api",
    "3rd party api",
    "api integration",
    "harici api",
    "dış api",
    "dis api",
    "entegrasyon",
)
_REALTIME_TERMS = (
    "real-time",
    "realtime",
    "live updates",
    "live data",
    "gerçek zamanlı",
    "gercek zamanli",
    "canlı veri",
    "canli veri",
)
_BOOKING_TERMS = ("booking", "reservation", "appointment", "rezervasyon", "randevu")
_COMMERCE_TERMS = (
    "ecommerce",
    "e-commerce",
    "cart",
    "checkout",
    "payment",
    "storefront",
    "ödeme",
    "odeme",
    "sepet",
    "mağaza",
    "magaza",
)
_CMS_TERMS = ("cms", "content management", "içerik yönet", "icerik yonet")

WebAppKind = Literal["dashboard", "admin", "portal", "application"]


class WebAppSpecError(ValueError):
    """A user objective cannot be represented safely as a bounded WebAppSpec."""


@dataclass(frozen=True, slots=True)
class WebAppResourceSpec:
    name: str
    operations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "operations": list(self.operations)}


@dataclass(frozen=True, slots=True)
class WebAppSpec:
    """Inspectable target requirements; capability availability is evaluated elsewhere."""

    app_id: str
    app_kind: WebAppKind
    objective_sha256: str
    locales: tuple[str, ...]
    auth_required: bool
    resources: tuple[WebAppResourceSpec, ...]
    tables_required: bool
    charts_required: bool
    external_api_required: bool
    realtime_required: bool
    booking_required: bool
    commerce_required: bool
    cms_required: bool
    reference_semantic_sha256: str | None
    reference_design_constraints: tuple[str, ...]
    acceptance_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["resources"] = [resource.to_dict() for resource in self.resources]
        return value

    @property
    def requested_capabilities(self) -> tuple[str, ...]:
        capabilities: list[str] = ["web-app", "responsive-ui"]
        if self.auth_required:
            capabilities.append("auth")
        if self.resources:
            capabilities.append("data")
            if any(
                resource.operations == ("create", "read", "update", "delete")
                for resource in self.resources
            ):
                capabilities.append("crud")
        if self.tables_required:
            capabilities.append("tables")
        if self.charts_required:
            capabilities.append("charts")
        if self.external_api_required:
            capabilities.append("external-api")
        if self.realtime_required:
            capabilities.append("realtime")
        if self.booking_required:
            capabilities.append("booking")
        if self.commerce_required:
            capabilities.append("commerce")
        if self.cms_required:
            capabilities.append("cms")
        return tuple(capabilities)

    @property
    def spec_sha256(self) -> str:
        canonical = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


def derive_web_app_spec(
    request_id: str,
    objective: str,
    *,
    semantic_brief: WebReferenceSemanticBrief | None = None,
) -> WebAppSpec:
    """Derive only requirements that are explicit enough to be audited."""
    if not request_id or request_id != request_id.strip() or len(request_id) > 160:
        raise WebAppSpecError("Web App request_id must be bounded and trimmed")
    if not objective or objective != objective.strip():
        raise WebAppSpecError("Web App objective must be non-blank and trimmed")
    if len(objective) > _MAX_OBJECTIVE_CHARS:
        raise WebAppSpecError("Web App objective exceeds the input limit")
    normalized = " ".join(objective.casefold().split())
    if any(term in normalized for term in _NON_WEB_PLATFORM_TERMS):
        raise WebAppSpecError("objective targets a non-Web application platform")
    if not any(term in normalized for term in _WEB_APP_TERMS):
        raise WebAppSpecError("objective does not explicitly target a Web application surface")

    kind = _kind(normalized)
    locales = _locales(normalized)
    auth_required = _contains(normalized, _AUTH_TERMS)
    crud_requested = _contains(normalized, _CRUD_TERMS)
    resource_names = _resource_names(normalized)
    if crud_requested and not resource_names:
        raise WebAppSpecError(
            "CRUD was requested without an explicit bounded resource (for example projects, tasks, orders, products, customers, bookings, invoices, tickets, documents, or users)"
        )
    operations = ("create", "read", "update", "delete") if crud_requested else ("read",)
    resources = tuple(WebAppResourceSpec(name, operations) for name in resource_names)

    tables_required = _contains(normalized, _TABLE_TERMS) or bool(resources)
    charts_required = _contains(normalized, _CHART_TERMS)
    external_api_required = _contains(normalized, _EXTERNAL_API_TERMS)
    realtime_required = _contains(normalized, _REALTIME_TERMS)
    booking_required = _contains(normalized, _BOOKING_TERMS)
    commerce_required = _contains(normalized, _COMMERCE_TERMS)
    cms_required = _contains(normalized, _CMS_TERMS)
    if booking_required:
        booking_ops = operations if crud_requested else ("create", "read")
        if "bookings" in resource_names:
            resources = tuple(
                WebAppResourceSpec(item.name, booking_ops)
                if item.name == "bookings"
                else item
                for item in resources
            )
        else:
            resources = (*resources, WebAppResourceSpec("bookings", booking_ops))
        tables_required = True
    if commerce_required and not any(name in resource_names for name in ("orders", "products")):
        raise WebAppSpecError(
            "commerce was requested without explicit products or orders requirements"
        )

    semantic_sha: str | None = None
    design_constraints: tuple[str, ...] = ()
    if semantic_brief is not None:
        semantic_sha = semantic_brief.analysis_sha256
        allowed = {"layout", "component", "navigation", "typography", "color", "spacing", "surface", "content_hierarchy", "interaction", "responsive", "fidelity"}
        design_constraints = tuple(
            f"{item.category}: {item.text}"
            for item in semantic_brief.observations
            if item.category in allowed
        )
        if not design_constraints:
            raise WebAppSpecError("reference semantic brief contains no usable design constraints")

    objective_sha = hashlib.sha256(objective.encode("utf-8")).hexdigest()
    app_id = f"webapp-{hashlib.sha256(f'{request_id}\0{objective}'.encode()).hexdigest()[:20]}"
    acceptance = _acceptance_requirements(
        auth_required=auth_required,
        resources=resources,
        tables_required=tables_required,
        charts_required=charts_required,
        external_api_required=external_api_required,
        realtime_required=realtime_required,
        booking_required=booking_required,
        commerce_required=commerce_required,
        cms_required=cms_required,
        has_references=semantic_brief is not None,
    )
    return WebAppSpec(
        app_id=app_id,
        app_kind=kind,
        objective_sha256=objective_sha,
        locales=locales,
        auth_required=auth_required,
        resources=resources,
        tables_required=tables_required,
        charts_required=charts_required,
        external_api_required=external_api_required,
        realtime_required=realtime_required,
        booking_required=booking_required,
        commerce_required=commerce_required,
        cms_required=cms_required,
        reference_semantic_sha256=semantic_sha,
        reference_design_constraints=design_constraints,
        acceptance_requirements=acceptance,
    )


def _contains(normalized: str, terms: tuple[str, ...]) -> bool:
    return any(term in normalized for term in terms)


def _kind(normalized: str) -> WebAppKind:
    if any(term in normalized for term in ("admin panel", "yönetim paneli", "yonetim paneli")):
        return "admin"
    if any(term in normalized for term in ("customer portal", "client portal", "müşteri portalı", "musteri portali")):
        return "portal"
    if "dashboard" in normalized:
        return "dashboard"
    return "application"


def _locales(normalized: str) -> tuple[str, ...]:
    bilingual = any(
        term in normalized
        for term in (
            "bilingual",
            "turkish/english",
            "english/turkish",
            "türkçe/ingilizce",
            "ingilizce/türkçe",
        )
    )
    turkish = any(term in normalized for term in ("türkçe", "turkish", "turkce"))
    english = any(term in normalized for term in ("english", "ingilizce"))
    if bilingual or (turkish and english):
        return ("en", "tr")
    return ("tr",) if turkish else ("en",)


def _resource_names(normalized: str) -> tuple[str, ...]:
    names = tuple(
        name
        for name, terms in _RESOURCE_TERMS
        if any(_term_present(normalized, term) for term in terms)
    )
    if len(names) > _MAX_RESOURCES:
        raise WebAppSpecError("Web App resource count exceeds the bounded limit")
    return names


def _term_present(normalized: str, term: str) -> bool:
    if " " in term or any(ord(character) > 127 for character in term):
        return term in normalized
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", normalized) is not None


def _acceptance_requirements(
    *,
    auth_required: bool,
    resources: tuple[WebAppResourceSpec, ...],
    tables_required: bool,
    charts_required: bool,
    external_api_required: bool,
    realtime_required: bool,
    booking_required: bool,
    commerce_required: bool,
    cms_required: bool,
    has_references: bool,
) -> tuple[str, ...]:
    values = [
        "responsive browser-rendered application routes pass",
        "accessibility, security, performance, and visual QA evidence pass",
        "exact generated/revised source digest is bound to acceptance evidence",
    ]
    if auth_required:
        values.append("unauthenticated protected-route and API access fails closed")
    if resources:
        values.append("declared data resource operations pass exact contract tests")
    if tables_required:
        values.append("table states cover loading, empty, error, and populated data")
    if charts_required:
        values.append("chart values are derived from authenticated application data")
    if external_api_required:
        values.append("external API egress is allowlisted and secrets stay server-side")
    if realtime_required:
        values.append("realtime disconnect/reconnect and stale-state behavior is tested")
    if booking_required:
        values.append("booking conflicts and idempotency are tested")
    if commerce_required:
        values.append("commerce mutation and payment actions require explicit governed adapters")
    if cms_required:
        values.append("content mutation is authenticated, validated, and auditable")
    if has_references:
        values.append("reference semantic evidence is bound to visual-fidelity acceptance")
    return tuple(values)
