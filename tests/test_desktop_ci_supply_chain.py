"""Tests for the fail-closed Desktop CI supply-chain policy."""

from __future__ import annotations

from pathlib import Path

from services.desktop_ci_supply_chain import (
    DESKTOP_WORKFLOWS,
    DesktopCISupplyChainPolicy,
)


def test_repository_desktop_workflows_pass_supply_chain_policy() -> None:
    root = Path(__file__).resolve().parents[1]
    report = DesktopCISupplyChainPolicy().audit(root)
    assert report.passed, report.findings


def test_mutable_action_and_persisted_checkout_are_blocked(tmp_path: Path) -> None:
    for relative in DESKTOP_WORKFLOWS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith("desktop-msix-signed-release.yml"):
            path.write_text(
                "permissions:\n  contents: read\n"
                "environment: desktop-release-signing\n"
                "steps:\n"
                "  - uses: actions/checkout@v4\n"
                "    with:\n"
                "      ref: ${{ github.sha }}\n"
                "  - run: flutter pub get --enforce-lockfile\n"
                "  - run: echo ${{ secrets.ILAIOS_WINDOWS_SIGNING_PFX_BASE64 }}\n"
                "  - run: echo ${{ secrets.ILAIOS_WINDOWS_SIGNING_PFX_PASSWORD }}\n"
                "  - name: Remove certificate material\n"
                "    if: always()\n"
                "    run: echo cleanup\n",
                encoding="utf-8",
            )
        else:
            path.write_text(
                "permissions:\n  contents: read\n"
                "steps:\n"
                "  - uses: actions/checkout@v4\n"
                "    with:\n"
                "      ref: ${{ github.sha }}\n"
                "  - run: flutter pub get --enforce-lockfile\n",
                encoding="utf-8",
            )

    report = DesktopCISupplyChainPolicy().audit(tmp_path)
    ids = {item.finding_id for item in report.findings}
    assert "DESKTOP-CI-MUTABLE-ACTION" in ids
    assert "DESKTOP-CI-CHECKOUT-CREDENTIALS" in ids
