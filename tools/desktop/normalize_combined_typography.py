from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
v10_rel = "apps/desktop/lib/features/dashboard/reference_desktop_shell_v10.dart"
deliveries_rel = "apps/desktop/lib/features/deliveries/deliveries_view.dart"
test_rel = "apps/desktop/test/desktop_combined_typography_reference_ux_test.dart"


def head_text(rel: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"HEAD:{rel}"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"SCOPED_TYPOGRAPHY_ANCHOR_MISMATCH {label}: expected 1, actual {count}"
        )
    return text.replace(old, new, 1)


def replace_once_in_region(
    text: str,
    region_start: str,
    region_end: str,
    old: str,
    new: str,
    label: str,
) -> str:
    start_count = text.count(region_start)
    end_count = text.count(region_end)
    if start_count != 1 or end_count != 1:
        raise SystemExit(
            f"SCOPED_TYPOGRAPHY_REGION_MISMATCH {label}: "
            f"start={start_count}, end={end_count}"
        )
    start = text.index(region_start)
    end = text.index(region_end, start)
    if end <= start:
        raise SystemExit(f"SCOPED_TYPOGRAPHY_REGION_ORDER_MISMATCH {label}")
    region = text[start:end]
    count = region.count(old)
    if count != 1:
        raise SystemExit(
            f"SCOPED_TYPOGRAPHY_ANCHOR_MISMATCH {label}: expected 1 in region, actual {count}"
        )
    updated_region = region.replace(old, new, 1)
    return text[:start] + updated_region + text[end:]


# Preserve the canonical shell exactly. The previous candidate applied a global
# 1.10 MediaQuery text scale, which enlarged unrelated Settings, Approvals,
# Live Workspace, toolbar and filter geometry. The requested readability change
# is scoped to Outputs content instead; sidebar/topbar/shell geometry and scale
# remain byte-for-byte at the checked-out branch baseline.
v10_path = root / v10_rel
v10_path.write_text(head_text(v10_rel), encoding="utf-8", newline="\n")
print("V10_TYPOGRAPHY_PRESERVED_NO_GLOBAL_ZOOM")

# Rebuild Outputs from the exact checked-out branch source so the aggressive
# whole-file font-size mapping from the candidate patch cannot leak into fixed
# KPI/toolbar/filter geometry. Then uplift only unconstrained, ellipsis-safe
# reading surfaces by about 15-20 percent.
deliveries = head_text(deliveries_rel)
deliveries = replace_once(
    deliveries,
    "                          fontSize: 22,\n                          fontWeight: FontWeight.w700,",
    "                          fontSize: 25.5,\n                          fontWeight: FontWeight.w700,",
    "outputs-title",
)
deliveries = replace_once(
    deliveries,
    "                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 10.5),",
    "                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 12.2),",
    "outputs-subtitle",
)
deliveries = replace_once(
    deliveries,
    "          style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),",
    "          style: const TextStyle(fontSize: 9.8, fontWeight: FontWeight.w600),",
    "outputs-table-header",
)
deliveries = replace_once(
    deliveries,
    "                          style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700),",
    "                          style: const TextStyle(fontSize: 11.0, fontWeight: FontWeight.w700),",
    "outputs-row-title",
)
deliveries = replace_once_in_region(
    deliveries,
    "class _OutputRow extends StatelessWidget {",
    "class _UnavailableCell extends StatelessWidget {",
    "                          style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 7.5),",
    "                          style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 8.7),",
    "outputs-row-subtitle",
)
deliveries = replace_once(
    deliveries,
    "              child: Text(size, style: const TextStyle(fontSize: 8.5)),",
    "              child: Text(size, style: const TextStyle(fontSize: 9.8)),",
    "outputs-row-size",
)
deliveries = replace_once(
    deliveries,
    "                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),",
    "                style: const TextStyle(fontSize: 12.7, fontWeight: FontWeight.w700),",
    "outputs-empty-title",
)

# The 1366x768 Desktop content rail leaves about 791px for Outputs filters and
# about 773px for the toolbar. Keep every control visible and preserve its font
# size/semantics by compacting only fixed horizontal geometry inside Outputs.
# Scope generic literals to their owning widgets so unrelated matching values
# cannot make the fail-closed normalizer ambiguous as the Outputs lifecycle grows.
deliveries = replace_once_in_region(
    deliveries,
    "class _Toolbar extends StatelessWidget {",
    "class _Filters extends StatelessWidget {",
    "          padding: const EdgeInsets.symmetric(horizontal: 10),",
    "          padding: const EdgeInsets.symmetric(horizontal: 7),",
    "outputs-tab-horizontal-padding",
)
deliveries = replace_once(
    deliveries,
    "              width: 185,",
    "              width: 145,",
    "outputs-search-width",
)
deliveries = replace_once(
    deliveries,
    "              width: 105,",
    "              width: 90,",
    "outputs-type-filter-width",
)
deliveries = replace_once_in_region(
    deliveries,
    "class _Filters extends StatelessWidget {",
    "class _FilterDropdown extends StatelessWidget {",
    "              width: 118,",
    "              width: 100,",
    "outputs-date-filter-width",
)
(root / deliveries_rel).write_text(deliveries, encoding="utf-8", newline="\n")
print("OUTPUTS_TYPOGRAPHY_SCOPED_UPLIFT_APPLIED")
print("OUTPUTS_COMPACT_CONTROL_GEOMETRY_APPLIED")

# Replace the generated regression assertion that previously required a global
# 1.10 scaler. The new contract explicitly proves no global zoom, then checks
# the scoped Outputs title uplift and overflow safety at every required viewport.
test_path = root / test_rel
test_text = test_path.read_text(encoding="utf-8")
old_assertion = """        final homeNav = find.byKey(const ValueKey('nav-home'));
        final homeText =
            find.descendant(of: homeNav, matching: find.byType(Text)).first;
        final scaler = MediaQuery.textScalerOf(tester.element(homeText));
        expect(
          scaler.scale(1.0),
          greaterThanOrEqualTo(1.10),
          reason:
              'Desktop typography uplift was not active at ${size.width}x${size.height}',
        );

        await _openGoals(tester);
"""
new_assertion = """        final homeNav = find.byKey(const ValueKey('nav-home'));
        final homeText =
            find.descendant(of: homeNav, matching: find.byType(Text)).first;
        final scaler = MediaQuery.textScalerOf(tester.element(homeText));
        expect(
          scaler.scale(1.0),
          closeTo(.95, .001),
          reason:
              'Desktop shell must retain its canonical scale at ${size.width}x${size.height}',
        );

        await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
        await tester.pumpAndSettle();
        final outputsHeader = find.byKey(const Key('outputs-header'));
        expect(outputsHeader, findsOneWidget);
        final outputsTitle = find.descendant(
          of: outputsHeader,
          matching: find.text('Outputs'),
        );
        expect(outputsTitle, findsOneWidget);
        expect(tester.widget<Text>(outputsTitle).style?.fontSize, 25.5);
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Scoped Outputs typography overflowed at ${size.width}x${size.height}',
        );

        await _openGoals(tester);
"""
test_text = replace_once(
    test_text,
    old_assertion,
    new_assertion,
    "viewport-global-scale-assertion",
)
test_path.write_text(test_text, encoding="utf-8", newline="\n")
print("COMBINED_VIEWPORT_TEST_SCOPED_TYPOGRAPHY_ASSERTION_APPLIED")
