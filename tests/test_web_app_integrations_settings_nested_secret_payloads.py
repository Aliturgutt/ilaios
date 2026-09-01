from __future__ import annotations

import pytest

from services.web_app_integrations_settings_runtime import (
    WebAppIntegrationsSettingsError,
    WebAppIntegrationsSettingsRuntime,
)


def _runtime_without_backends() -> WebAppIntegrationsSettingsRuntime:
    return object.__new__(WebAppIntegrationsSettingsRuntime)


def test_nested_secret_key_in_mapping_fails_closed() -> None:
    runtime = _runtime_without_backends()

    with pytest.raises(WebAppIntegrationsSettingsError) as exc:
        runtime._safe_payload({"meta": {"api_key": "must-not-cross-capability-boundary"}})

    assert exc.value.code == "SECRET_PAYLOAD_FORBIDDEN"


def test_nested_secret_key_inside_list_fails_closed() -> None:
    runtime = _runtime_without_backends()

    with pytest.raises(WebAppIntegrationsSettingsError) as exc:
        runtime._safe_payload(
            {"items": [{"name": "safe"}, {"details": {"access-token": "forbidden"}}]}
        )

    assert exc.value.code == "SECRET_PAYLOAD_FORBIDDEN"


def test_nested_non_secret_payload_remains_supported() -> None:
    runtime = _runtime_without_backends()

    encoded = runtime._safe_payload(
        {
            "meta": {"region": "eu", "retry": False},
            "items": [{"name": "Ada", "labels": ["customer", "priority"]}],
        }
    )

    assert "Ada" in encoded
    assert "region" in encoded
