from __future__ import annotations

import json
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

from apps.web_app_runtime.login_server import LoginAppRuntime
from apps.web_app_runtime.server import RuntimeRequest
from services.commercial_access import CommercialAccessStore, EntitlementState
from services.commercial_plans import commercial_plan_ids, get_commercial_plan
from services.subscription_presentation import plan_catalog
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from tests.test_app_ilaios_http_runtime import (
    _NOW, _callback, _cookie_header, _runtime,
)


def _login_runtime(tmp_path: Path) -> LoginAppRuntime:
    base, _ = _runtime(tmp_path / "identity.db")
    return LoginAppRuntime(
        environment=base.environment, oauth=base.oauth, sessions=base.sessions,
        browser=base.browser, desktop_client_id=base.desktop_client_id,
    )


def test_catalog_projects_only_canonical_values() -> None:
    for locale, currency in (("tr", "TRY"), ("en", "USD")):
        catalog = plan_catalog(locale, currency)
        assert catalog["currency"] == currency
        plans = catalog["plans"]
        assert isinstance(plans, list)
        assert [p["plan_id"] for p in plans] == list(commercial_plan_ids())
        for item in plans:
            canonical = get_commercial_plan(item["plan_id"])
            assert item["storage_limit_gb"] == canonical.storage_limit_gb
            assert item["video_pool_minutes"] == canonical.monthly_video_pool_mini_480p_equivalent_minutes
            assert item["max_video_resolution"] == canonical.max_video_resolution
            assert item["parent"] == canonical.parent
            assert "monthly_provider_budget_usd" not in item
            if currency == "TRY" and canonical.monthly_price_usd != 0:
                assert item["monthly_price"] is None


def test_invalid_presentation_parameters_fail_closed(tmp_path: Path) -> None:
    runtime = _login_runtime(tmp_path)
    for query in (
        "lang=de", "lang=", "lang=tr&lang=en", "currency=EUR",
        "lang=en&currency=TRY", "price=1", "plan_id=POWER",
    ):
        response = runtime.dispatch(
            RuntimeRequest("GET", "/api/subscription/plans?" + query, {}), now=_NOW
        )
        assert response.status == HTTPStatus.BAD_REQUEST


def test_page_and_assets_render(tmp_path: Path) -> None:
    runtime = _login_runtime(tmp_path)
    for locale, title in (
        ("tr", "Planlar ve abonelik"),
        ("en", "Plans &amp; subscription"),
    ):
        response = runtime.dispatch(
            RuntimeRequest("GET", "/subscription?lang=" + locale, {}), now=_NOW
        )
        assert response.status == HTTPStatus.OK
        html = response.body.decode()
        assert f'lang="{locale}" data-theme="light"' in html
        assert title in html or title.replace("&amp;", "&") in html
        assert all(f'id="plan-{plan}"' in html for plan in commercial_plan_ids())
        assert "disabled" in html and "showModal" not in html
        assert "mailto:contact@ilaios.com" in html
        assert "<script>" not in html
        assert "frame-ancestors 'none'" in dict(response.headers)["Content-Security-Policy"]
        assert "no-store" == dict(response.headers)["Cache-Control"]
        for path in ("/subscription/styles.css", "/subscription/app.js"):
            assert runtime.dispatch(
                RuntimeRequest("GET", path, {}), now=_NOW
            ).status == HTTPStatus.OK
        css = runtime.dispatch(
            RuntimeRequest("GET", "/subscription/styles.css", {}), now=_NOW
        ).body
        assert b"data-theme=dark" in css
        assert b"gradient" not in css
        script = runtime.dispatch(
            RuntimeRequest("GET", "/subscription/app.js", {}), now=_NOW
        ).body
        assert b"textContent" in script and b"innerHTML" not in script
        assert b"normalizeBrandBackground" not in script
        assert b"ilaios-theme" in script


def test_default_is_turkish_and_links_from_login(tmp_path: Path) -> None:
    runtime = _login_runtime(tmp_path)
    page = runtime.dispatch(RuntimeRequest("GET", "/subscription", {}), now=_NOW)
    assert b'lang="tr"' in page.body
    assert "TL fiyatı bekleniyor" in page.body.decode()
    root = runtime.dispatch(RuntimeRequest("GET", "/", {}), now=_NOW)
    assert b'href="/subscription?lang=tr"' in root.body


def test_anonymous_and_forged_session_rejected(tmp_path: Path) -> None:
    runtime = _login_runtime(tmp_path)
    header_cases: list[dict[str, str]] = [
        {},
        {"Cookie": "__Host-ilaios_auth=fake; __Host-ilaios_session=fake"},
    ]
    for headers in header_cases:
        result = runtime.dispatch(
            RuntimeRequest("GET", "/api/subscription", headers), now=_NOW
        )
        assert result.status in {HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED}


def test_current_plan_uses_session_tenant_and_expiry(tmp_path: Path) -> None:
    runtime = _login_runtime(tmp_path)
    cookies, token, session_id = _callback(runtime)
    principal = runtime.sessions.verify(session_id, token, _NOW)
    request = RuntimeRequest("GET", "/api/subscription", {"Cookie": _cookie_header(cookies)})
    # Missing runtime wiring does not invent a Free subscription.
    response = runtime.dispatch(request, now=_NOW)
    assert json.loads(response.body)["current_plan"]["status"] == "UNKNOWN"
    store = CommercialAccessStore(tmp_path / "commercial", ManagedCreditLedgerStore(tmp_path / "credits"))
    runtime.commercial_access = store
    store.apply_entitlement(event_id="other", tenant_id="other-tenant", user_id=principal.principal_id,
                            plan_id="POWER", state=EntitlementState.ACTIVE, valid_until=None,
                            paid_provider_allowed=True, now=_NOW)
    assert json.loads(runtime.dispatch(request, now=_NOW).body)["current_plan"]["plan_id"] is None
    store.apply_entitlement(event_id="own", tenant_id=principal.tenant_id, user_id=principal.principal_id,
                            plan_id="PRO", state=EntitlementState.ACTIVE, valid_until=_NOW+timedelta(minutes=10),
                            paid_provider_allowed=True, now=_NOW)
    body = json.loads(runtime.dispatch(request, now=_NOW).body)
    assert body["current_plan"]["plan_id"] == "PRO"
    assert body["current_plan"]["status"] == "ACTIVE"
    assert body["current_plan"]["renewal"] is None
    assert body["current_plan"]["usage"] is None
    assert not any(body["actions"].values())
    expired = runtime.dispatch(request, now=_NOW+timedelta(minutes=11))
    assert json.loads(expired.body)["current_plan"]["status"] == "EXPIRED"
    # The existing canonical logout makes the projection inaccessible too.
    logout_headers = {"Cookie": _cookie_header(cookies), "Origin": "https://app.ilaios.com",
                      "X-CSRF-Token": cookies["__Host-ilaios_csrf"]}
    runtime.dispatch(RuntimeRequest("POST", "/auth/logout", logout_headers), now=_NOW)
    assert runtime.dispatch(request, now=_NOW).status != HTTPStatus.OK


def test_checkout_rejects_forged_authority(tmp_path: Path) -> None:
    runtime = _login_runtime(tmp_path)
    cookies, _, _ = _callback(runtime)
    headers = {"Cookie": _cookie_header(cookies), "Origin": "https://app.ilaios.com",
               "X-CSRF-Token": cookies["__Host-ilaios_csrf"]}
    changes_cases: tuple[dict[str, object], ...] = (
        {"payment_success": True},
        {"subscription_active": True},
        {"price": 1},
        {"tenant_id": "other"},
        {"plan_id": "UNKNOWN"},
        {"locale": "de"},
        {"currency": "EUR"},
        {"currency": "TRY"},
        {"plan_id": ["POWER"]},
    )
    for changes in changes_cases:
        payload: dict[str, object] = {
            "plan_id": "PRO", "locale": "en", "currency": "USD",
        }
        payload.update(changes)
        result = runtime.dispatch(
            RuntimeRequest(
                "POST", "/api/subscription/checkout", headers,
                body=json.dumps(payload).encode(),
            ),
            now=_NOW,
        )
        assert result.status == HTTPStatus.BAD_REQUEST


def test_valid_checkout_still_denied_and_csrf_required(tmp_path: Path) -> None:
    runtime = _login_runtime(tmp_path)
    cookies, _, _ = _callback(runtime)
    headers = {"Cookie": _cookie_header(cookies), "Origin": "https://app.ilaios.com",
               "X-CSRF-Token": cookies["__Host-ilaios_csrf"]}
    body = b'{"plan_id":"PRO","locale":"en","currency":"USD"}'
    result = runtime.dispatch(RuntimeRequest("POST", "/api/subscription/checkout", headers, body=body), now=_NOW)
    assert result.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert json.loads(result.body)["available"] is False
    assert json.loads(result.body)["final_price"] is None
    headers.pop("X-CSRF-Token")
    denied = runtime.dispatch(RuntimeRequest("POST", "/api/subscription/checkout", headers, body=body), now=_NOW)
    assert denied.status == HTTPStatus.FORBIDDEN
    assert runtime.commercial_access is None
