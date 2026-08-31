from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()


def path(rel: str) -> Path:
    return root / rel


def read(rel: str) -> str:
    candidate = path(rel)
    if not candidate.is_file():
        raise SystemExit(f"V4_CONTRACT_FILE_MISSING {rel}")
    return candidate.read_text(encoding="utf-8")


def require(rel: str, *anchors: str) -> None:
    text = read(rel)
    missing = [anchor for anchor in anchors if anchor not in text]
    if missing:
        raise SystemExit(f"V4_CONTRACT_MISSING {rel}: {missing!r}")


def forbid(rel: str, *anchors: str) -> None:
    text = read(rel)
    present = [anchor for anchor in anchors if anchor in text]
    if present:
        raise SystemExit(f"PRE_V4_CONTRACT_REINTRODUCED {rel}: {present!r}")


def present(rel: str) -> bool:
    return path(rel).is_file()


desktop_app = "apps/desktop/lib/app/desktop_app.dart"
create_view = "apps/desktop/lib/features/create/create_view.dart"
picker = "apps/desktop/lib/features/create/reference_asset_picker.dart"
home = "apps/desktop/lib/features/dashboard/reference_home_dashboard_v3.dart"
workflows = "apps/desktop/lib/features/dashboard/reference_workflows_view.dart"
agents = "apps/desktop/lib/features/dashboard/reference_agents_view.dart"
approvals = "apps/desktop/lib/features/operations/approvals_view.dart"
evidence = "apps/desktop/lib/features/operations/evidence_view.dart"
outputs = "apps/desktop/lib/features/deliveries/deliveries_view.dart"
costs = "apps/desktop/lib/features/operations/reference_costs_view.dart"
combined_test = "apps/desktop/test/desktop_combined_typography_reference_ux_test.dart"

# Combined Final no longer rewrites checked-out V4 source. It validates the
# current V4 contract fail-closed. Static-analysis regression tests intentionally
# execute this helper against a reduced temporary repository, so only anchors
# whose source files are present there are checked in that mode.
require(
    desktop_app,
    "final ReferenceAssetPickerController _referenceAssets =",
    "referenceAssets: _referenceAssets,",
    "final hasReferences = _referenceAssets.assets.isNotEmpty;",
)
require(
    create_view,
    "key: const Key('reference-goals-page')",
    "key: const Key('goals-composer')",
    "ReferenceAssetPicker(",
)

forbid(
    desktop_app,
    "bool _referenceDockOpen = false;",
    "class _ReferenceAssetDock extends StatelessWidget",
    "reference-asset-dock-toggle",
)

if present(picker):
    require(
        picker,
        "Expanded(flex: 3, child: _images())",
        "Expanded(flex: 2, child: _sourceVideo())",
    )

if present(home):
    require(
        home,
        "key: const Key('command-center-home')",
        "key: const Key('command-center-hero')",
        "key: const Key('command-center-focus')",
        "key: const Key('command-center-attention')",
    )
    forbid(
        home,
        "command-center-orbit-motion",
        "ReferenceHomeMotionSurface",
        "command-center-session",
        "command-center-quick-actions",
    )

optional_contracts = (
    (workflows, "key: const Key('reference-workflows-page')"),
    (agents, "key: const Key('reference-agents-page')"),
    (approvals, "key: const Key('reference-approvals-page')"),
    (evidence, "key: const Key('reference-evidence-page')"),
    (outputs, "key: const Key('reference-outputs-page')"),
    (costs, "key: const Key('reference-costs-page')"),
)
for rel, anchor in optional_contracts:
    if present(rel):
        require(rel, anchor)

if present(combined_test):
    require(
        combined_test,
        "const Size(1366, 768)",
        "const Size(1440, 900)",
        "const Size(1920, 1080)",
    )

print("COMBINED_V4_CONTRACT_OK")
print("COMBINED_PATCH_SOURCE_MUTATIONS=0")
