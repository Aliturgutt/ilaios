from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()


def path(rel: str) -> Path:
    return root / rel


def read(rel: str) -> str:
    candidate = path(rel)
    if not candidate.is_file():
        raise SystemExit(f"DESKTOP_7_PAGE_CONTRACT_FILE_MISSING {rel}")
    return candidate.read_text(encoding="utf-8")


def require(rel: str, *anchors: str) -> None:
    text = read(rel)
    missing = [anchor for anchor in anchors if anchor not in text]
    if missing:
        raise SystemExit(f"DESKTOP_7_PAGE_CONTRACT_MISSING {rel}: {missing!r}")


def forbid(rel: str, *anchors: str) -> None:
    text = read(rel)
    present = [anchor for anchor in anchors if anchor in text]
    if present:
        raise SystemExit(f"SUPERSEDED_DESKTOP_CONTRACT_REINTRODUCED {rel}: {present!r}")


shell = "apps/desktop/lib/features/dashboard/reference_desktop_shell_v11.dart"
picker = "apps/desktop/lib/features/create/reference_asset_picker.dart"
outputs = "apps/desktop/lib/features/deliveries/deliveries_view.dart"

# This legacy-named helper is retained only because existing CI references its
# path. It no longer validates or mutates V4 visuals. The current contract is
# the canonical seven-page Desktop shell plus bounded Home attachment behavior.
require(
    shell,
    "class ReferenceDesktopShellV11",
    "DesktopSection.home,",
    "DesktopSection.workflows,",
    "DesktopSection.agents,",
    "DesktopSection.artifacts,",
    "DesktopSection.approvals,",
    "DesktopSection.evidence,",
    "DesktopSection.settings,",
    "key: const Key('reference-responsive-viewport-v11')",
    "key: const Key('canonical-7-page-sidebar')",
    "key: const Key('canonical-7-page-topbar')",
)
forbid(
    shell,
    "DesktopSection.goals,",
    "DesktopSection.live,",
    "DesktopSection.costs,",
    "reference-secondary-navigation",
    "TextScaler.linear(desktopTextScale)",
    "TextScaler.linear(.95)",
)
require(
    picker,
    "key: const Key('home-add-document')",
    "key: const Key('home-add-image')",
    "key: const Key('home-add-video')",
    "content: SizedBox(width: 620, child: body)",
    "key: const Key('home-canonical-factory-grid')",
)
require(outputs, "key: const Key('reference-outputs-page')")

print("DESKTOP_7_PAGE_CONTRACT_OK")
print("COMBINED_PATCH_SOURCE_MUTATIONS=0")
