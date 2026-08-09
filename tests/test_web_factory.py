"""Real golden Web Factory workflow tests for PLATFORM.P17."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.integrations import GovernedWebFactory
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy


def _grant(now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        "web-grant",
        "web-worker",
        frozenset({"web.build"}),
        frozenset({"ilaios-official"}),
        now + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def test_golden_official_site_writes_addressable_verified_bundle(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pages = ("home", "product", "security", "contact")
    result = GovernedWebFactory(GrantPolicy(), tmp_path / "artifacts").build_official_site(
        "ilaios-official", pages, grant=_grant(now), now=now
    )
    bundle = Path(result.bundle_path)

    assert result.accepted is True
    assert result.official_brand == "ILAIOS"
    assert result.bundle_id.endswith(result.artifact_hash[:20])
    assert bundle.is_dir()
    actual_files = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file()
    }
    assert actual_files == {
        "acceptance.json",
        "assets/site.css",
        "contact.html",
        "home.html",
        "product.html",
        "security.html",
    }
    for item in result.files:
        content = (bundle / item.relative_path).read_bytes()
        assert len(content) == item.size
        assert hashlib.sha256(content).hexdigest() == item.sha256
    manifest = json.loads((bundle / "acceptance.json").read_text())
    assert manifest["accepted"] is True
    assert manifest["artifact_hash"] == result.artifact_hash
    assert manifest["bundle_id"] == result.bundle_id


def test_rebuild_is_stable_and_tampered_bundle_is_rejected(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pages = ("home", "product", "security", "contact")
    root = tmp_path / "artifacts"
    first = GovernedWebFactory(GrantPolicy(), root).build_official_site(
        "ilaios-official", pages, grant=_grant(now), now=now
    )
    second = GovernedWebFactory(GrantPolicy(), root).build_official_site(
        "ilaios-official", pages, grant=_grant(now), now=now
    )
    assert second == first

    (Path(first.bundle_path) / "home.html").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="tampered"):
        GovernedWebFactory(GrantPolicy(), root).build_official_site(
            "ilaios-official", pages, grant=_grant(now), now=now
        )


def test_golden_workflow_rejects_incomplete_site(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="canonical page set"):
        GovernedWebFactory(GrantPolicy(), tmp_path).build_official_site(
            "ilaios-official", ("home",), grant=_grant(now), now=now
        )
