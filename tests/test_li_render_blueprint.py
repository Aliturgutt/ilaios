from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _render_service() -> dict[str, Any]:
    document = yaml.safe_load(Path("render.yaml").read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    services = document.get("services")
    assert isinstance(services, list)
    matches = [
        service
        for service in services
        if isinstance(service, dict) and service.get("name") == "ilaios-web-app"
    ]
    assert len(matches) == 1
    return matches[0]


def test_li_production_activation_vars_are_manual_and_atomic() -> None:
    service = _render_service()
    env_vars = service.get("envVars")
    assert isinstance(env_vars, list)

    values = {
        item["key"]: item
        for item in env_vars
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    }
    li_keys = (
        "ILAIOS_LI_DATABASE_PATH",
        "ILAIOS_LI_FOUNDER_USER_ID",
        "ILAIOS_LI_FOUNDER_TENANT_ID",
    )
    for key in li_keys:
        assert key in values
        assert values[key].get("sync") is False
        assert "value" not in values[key]
        assert "generateValue" not in values[key]


def test_li_and_canonical_identity_use_distinct_persistent_database_paths() -> None:
    service = _render_service()
    disk = service.get("disk")
    assert isinstance(disk, dict)
    assert disk.get("mountPath") == "/var/data"

    env_vars = service.get("envVars")
    assert isinstance(env_vars, list)
    identity = next(
        item
        for item in env_vars
        if isinstance(item, dict)
        and item.get("key") == "ILAIOS_IDENTITY_DATABASE_PATH"
    )
    assert identity.get("value") == "/var/data/ilaios_identity.db"

    render_text = Path("render.yaml").read_text(encoding="utf-8")
    assert "/var/data/ilaios_li.db" in render_text
    assert "/var/data/ilaios_li.db" != identity["value"]
