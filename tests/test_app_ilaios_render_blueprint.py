from __future__ import annotations

from pathlib import Path

import yaml


def test_app_ilaios_render_blueprint_is_bounded_and_persistent() -> None:
    blueprint = yaml.safe_load(Path("render.yaml").read_text(encoding="utf-8"))

    services = blueprint["services"]
    assert len(services) == 1
    service = services[0]

    assert service["type"] == "web"
    assert service["name"] == "ilaios-web-app"
    assert service["runtime"] == "python"
    assert service["region"] == "frankfurt"
    assert service["plan"] == "starter"
    assert service["branch"] == "master"
    assert service["startCommand"] == "python -m apps.web_app_runtime.server"
    assert service["healthCheckPath"] == "/health/ready"
    assert service["autoDeployTrigger"] == "checksPass"
    assert service["numInstances"] == 1
    assert service["domains"] == ["app.ilaios.com"]

    assert service["disk"] == {
        "name": "ilaios-identity",
        "mountPath": "/var/data",
        "sizeGB": 1,
    }

    env = {entry["key"]: entry for entry in service["envVars"]}
    assert env["ILAIOS_IDENTITY_DATABASE_PATH"]["value"] == (
        "/var/data/ilaios_identity.db"
    )
    assert env["ILAIOS_APP_HTTP_HOST"]["value"] == "0.0.0.0"
    assert env["ILAIOS_WEB_SESSION_LIFETIME_SECONDS"]["value"] == "3600"
    assert env["ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS"]["value"] == (
        "https://app.ilaios.com/auth/google/callback"
    )

    for key in (
        "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID",
        "ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID",
        "ILAIOS_GOOGLE_DESKTOP_CLIENT_ID",
        "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_SECRET",
    ):
        assert env[key] == {"key": key, "sync": False}

    assert env["ILAIOS_GOOGLE_WEB_OAUTH_STATE_SECRET"] == {
        "key": "ILAIOS_GOOGLE_WEB_OAUTH_STATE_SECRET",
        "generateValue": True,
    }


def test_app_ilaios_runtime_dependency_lock_is_minimal() -> None:
    requirements = Path("apps/web_app_runtime/requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()

    assert requirements == [
        "PyJWT==2.13.0",
        "python-dotenv==1.2.2",
        "requests==2.34.2",
    ]
