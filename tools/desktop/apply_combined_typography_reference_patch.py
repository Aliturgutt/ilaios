from pathlib import Path
import re
import sys

root = Path(sys.argv[1])


def p(rel):
    return root / Path(rel)


def read(rel):
    return p(rel).read_text(encoding="utf-8")


def write(rel, text):
    path = p(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"ANCHOR_MISMATCH {rel}: expected 1, actual {count}: {old[:100]!r}"
        )
    write(rel, text.replace(old, new, 1))


def replace_last(rel, old, new):
    text = read(rel)
    pos = text.rfind(old)
    if pos < 0:
        raise SystemExit(f"LAST_ANCHOR_MISMATCH {rel}: {old[:100]!r}")
    write(rel, text[:pos] + new + text[pos + len(old) :])


def replace_font_sizes(rel, mapping):
    text = read(rel)
    placeholders = {}
    total = 0
    for old, new in mapping.items():
        ph = f"__ILAIOS_FS_{old.replace('.', '_')}__"
        pattern = re.compile(r"fontSize:\s*" + re.escape(old) + r"(?=[,)])")
        text, n = pattern.subn(f"fontSize: {ph}", text)
        if n:
            placeholders[ph] = new
            total += n
    if total == 0:
        raise SystemExit(f"NO_FONT_REPLACEMENTS {rel}")
    for ph, new in placeholders.items():
        text = text.replace(ph, new)
    write(rel, text)
    print(f"FONT_REPLACEMENTS {rel}={total}")


v10 = "apps/desktop/lib/features/dashboard/reference_desktop_shell_v10.dart"
deliveries = "apps/desktop/lib/features/deliveries/deliveries_view.dart"
desktop_app = "apps/desktop/lib/app/desktop_app.dart"
create_view = "apps/desktop/lib/features/create/create_view.dart"
picker_core = "apps/desktop/lib/features/create/reference_asset_picker_core.dart"
identity = "apps/desktop/lib/identity/identity_client.dart"

# Typography uplift.
replace_once(
    v10,
    "    final media = MediaQuery.of(context);",
    "    final media = MediaQuery.of(context);\n"
    "    final systemTextScale = media.textScaler.scale(1.0);\n"
    "    final desktopTextScale = math.max(1.10, systemTextScale);",
)
replace_once(
    v10,
    "          data: media.copyWith(textScaler: const TextScaler.linear(.95)),",
    "          data: media.copyWith(textScaler: TextScaler.linear(desktopTextScale)),",
)
replace_font_sizes(
    v10,
    {
        "12.4": "12.8",
        "10.4": "11.0",
        "10.2": "11.5",
        "10": "11.0",
        "9.4": "10.8",
        "9.3": "11.5",
        "8.9": "10.5",
        "8.8": "10.5",
        "8.7": "10.5",
        "8.5": "10.5",
        "8.4": "10.5",
        "8": "10.5",
    },
)
replace_once(
    deliveries,
    "fontSize: 9.5, fontWeight: FontWeight.w700",
    "fontSize: 12.7, fontWeight: FontWeight.w700",
)
replace_font_sizes(
    deliveries,
    {
        "20": "21.0",
        "19": "21.0",
        "14": "15.0",
        "12": "12.7",
        "11": "12.5",
        "10.5": "12.0",
        "9.5": "11.5",
        "9": "11.0",
        "8.5": "11.0",
        "8.2": "10.8",
        "8": "10.5",
        "7.8": "10.5",
        "7.5": "10.5",
    },
)

# Shared Web/Video routing.
write(
    "apps/desktop/lib/reference_assets/reference_factory_target.dart",
    """enum ReferenceFactoryTarget { web, video }

const Set<String> referenceWebFactoryTerms = <String>{
  'website',
  'web site',
  'web sitesi',
  'landing page',
  'internet sitesi',
  'web app',
  'web application',
  'web uygulaması',
  'web uygulamasi',
  'dashboard',
  'admin panel',
  'management dashboard',
  'yönetim paneli',
  'yonetim paneli',
};

bool isVideoFactoryObjective(String objective) {
  final normalized = objective.trimLeft().toLowerCase();
  return normalized.startsWith('video creation task:') ||
      normalized.startsWith('video oluşturma görevi:');
}

bool isWebFactoryObjective(String objective) {
  final normalized = objective.trimLeft().toLowerCase();
  return referenceWebFactoryTerms.any(normalized.contains);
}

int referenceFactoryCount(String objective) {
  final video = isVideoFactoryObjective(objective);
  final web = isWebFactoryObjective(objective);
  return (video ? 1 : 0) + (web ? 1 : 0);
}

ReferenceFactoryTarget? resolveReferenceFactoryTarget(String objective) {
  if (referenceFactoryCount(objective) != 1) return null;
  return isVideoFactoryObjective(objective)
      ? ReferenceFactoryTarget.video
      : ReferenceFactoryTarget.web;
}
""",
)

write(
    "apps/desktop/lib/reference_assets/reference_asset_ui_scope.dart",
    """import 'package:flutter/widgets.dart';

import 'reference_factory_target.dart';

/// Presentation-only bridge between the compact prompt attachment control and
/// the existing governed reference-image dock.
///
/// This scope carries no upload authority. Raw bytes and server-side asset IDs
/// continue to flow through ReferenceAssetPickerController/IdentityClient.
class ReferenceAssetUiScope extends InheritedWidget {
  const ReferenceAssetUiScope({
    required this.count,
    required this.open,
    required this.enabled,
    required this.target,
    required this.onToggle,
    required this.onTargetChanged,
    required super.child,
    super.key,
  });

  final int count;
  final bool open;
  final bool enabled;
  final ReferenceFactoryTarget? target;
  final VoidCallback onToggle;
  final ValueChanged<ReferenceFactoryTarget?> onTargetChanged;

  static ReferenceAssetUiScope? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<ReferenceAssetUiScope>();

  @override
  bool updateShouldNotify(ReferenceAssetUiScope oldWidget) =>
      count != oldWidget.count ||
      open != oldWidget.open ||
      enabled != oldWidget.enabled ||
      target != oldWidget.target;
}
""",
)

# Desktop app: scope only, no shell geometry rewrite.
replace_once(
    desktop_app,
    "import '../identity/identity_client.dart';",
    "import '../identity/identity_client.dart';\n"
    "import '../reference_assets/reference_asset_ui_scope.dart';\n"
    "import '../reference_assets/reference_factory_target.dart';",
)
replace_once(
    desktop_app,
    "  bool _referenceDockOpen = false;",
    "  bool _referenceDockOpen = false;\n"
    "  ReferenceFactoryTarget? _referenceTarget;",
)
replace_once(
    desktop_app,
    "    super.initState();\n    WidgetsBinding.instance.addObserver(this);",
    "    super.initState();\n"
    "    _referenceAssets.addListener(_referenceAssetsChanged);\n"
    "    WidgetsBinding.instance.addObserver(this);",
)
replace_once(
    desktop_app,
    "      _referenceAssets.clear();\n      _referenceDockOpen = false;",
    "      _referenceAssets.clear();\n"
    "      _referenceDockOpen = false;\n"
    "      _referenceTarget = null;",
)
replace_once(
    desktop_app,
    "    _operationalRefreshTimer?.cancel();\n    _referenceAssets.dispose();",
    "    _operationalRefreshTimer?.cancel();\n"
    "    _referenceAssets.removeListener(_referenceAssetsChanged);\n"
    "    _referenceAssets.dispose();",
)
replace_once(
    desktop_app,
    "  void _restartOperationalRefresh() {",
    "  void _referenceAssetsChanged() {\n"
    "    if (mounted) setState(() {});\n"
    "  }\n\n"
    "  void _restartOperationalRefresh() {",
)

text = read(desktop_app)
text, n = re.subn(
    r"\nbool _isVideoFactoryObjective\(String objective\) \{.*\Z",
    "\n",
    text,
    flags=re.S,
)
if n != 1:
    raise SystemExit(f"DESKTOP_ROUTING_HELPER_REMOVAL expected 1 actual {n}")
text = text.replace("_referenceFactoryCount(", "referenceFactoryCount(")
text = text.replace("_isVideoFactoryObjective(", "isVideoFactoryObjective(")
text = text.replace(
    "final referenceFactoryCount = referenceFactoryCount(objective);",
    "final referenceTargetCount = referenceFactoryCount(objective);",
)
text = text.replace(
    "hasReferences && referenceFactoryCount",
    "hasReferences && referenceTargetCount",
)
write(desktop_app, text)

replace_once(
    desktop_app,
    "      home: IlaiosLocaleScope(",
    "      home: ReferenceAssetUiScope(\n"
    "        count: _referenceAssets.assets.length,\n"
    "        open: _referenceDockOpen,\n"
    "        enabled: widget.userSession != null &&\n"
    "            widget.projection.connected &&\n"
    "            widget.onPromptSubmit != null,\n"
    "        target: _referenceTarget,\n"
    "        onToggle: () =>\n"
    "            setState(() => _referenceDockOpen = !_referenceDockOpen),\n"
    "        onTargetChanged: (target) {\n"
    "          if (_referenceTarget != target) {\n"
    "            setState(() => _referenceTarget = target);\n"
    "          }\n"
    "        },\n"
    "        child: IlaiosLocaleScope(",
)
replace_last(
    desktop_app,
    "      ),\n    );\n  }\n}\n\nclass _ReferenceAssetDock",
    "      ),\n      ),\n    );\n  }\n}\n\nclass _ReferenceAssetDock",
)
replace_once(
    desktop_app,
    "                  controller: _referenceAssets,\n                  open: _referenceDockOpen,",
    "                  controller: _referenceAssets,\n"
    "                  target: _referenceTarget,\n"
    "                  open: _referenceDockOpen,",
)
replace_once(
    desktop_app,
    "    required this.controller,\n    required this.open,",
    "    required this.controller,\n"
    "    required this.target,\n"
    "    required this.open,",
)
replace_once(
    desktop_app,
    "  final ReferenceAssetPickerController controller;\n  final bool open;",
    "  final ReferenceAssetPickerController controller;\n"
    "  final ReferenceFactoryTarget? target;\n"
    "  final bool open;",
)
replace_once(
    desktop_app,
    "    final label = context.tr('referenceAssets.dock');",
    "    final label = _referenceDockBaseLabel(context, target);",
)
replace_once(
    desktop_app,
    "  final referenceSuffix = references == 0 ? '' : ' ($references/20)';",
    "  final referenceSuffix = references == 0 ? '' : ' · $references/20';",
)
replace_once(
    desktop_app,
    "String _dockLabel(\n",
    """String _referenceDockBaseLabel(
  BuildContext context,
  ReferenceFactoryTarget? target,
) {
  final tr = context.ilaiosLocale.locale == IlaiosLocale.turkish;
  return switch (target) {
    ReferenceFactoryTarget.web => tr ? 'Web referansları' : 'Web references',
    ReferenceFactoryTarget.video =>
      tr ? 'Video referansları' : 'Video references',
    null => context.tr('referenceAssets.dock'),
  };
}

String _dockLabel(
""",
)

# Compact attachment control in existing prompt field.
replace_once(
    create_view,
    "import '../../identity/identity_client.dart';",
    "import '../../identity/identity_client.dart';\n"
    "import '../../reference_assets/reference_asset_ui_scope.dart';\n"
    "import '../../reference_assets/reference_factory_target.dart';",
)
replace_once(
    create_view,
    "    final shouldReplace = current.isEmpty || starterTexts.contains(current);\n    setState(() {",
    "    final shouldReplace = current.isEmpty || starterTexts.contains(current);\n"
    "    final referenceTarget = switch (preset) {\n"
    "      _FactoryPreset.web => ReferenceFactoryTarget.web,\n"
    "      _FactoryPreset.video => ReferenceFactoryTarget.video,\n"
    "      _FactoryPreset.software => null,\n"
    "    };\n"
    "    ReferenceAssetUiScope.maybeOf(context)?.onTargetChanged(referenceTarget);\n"
    "    setState(() {",
)
replace_once(
    create_view,
    "                        prefixIcon: const Icon(Icons.track_changes_outlined, size: 16),\n"
    "                        contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),",
    "                        prefixIcon: const Icon(Icons.track_changes_outlined, size: 16),\n"
    "                        suffixIcon: ReferenceAssetUiScope.maybeOf(context) == null\n"
    "                            ? null\n"
    "                            : _ReferencePromptAttach(\n"
    "                                selectedPreset: selectedPreset,\n"
    "                              ),\n"
    "                        suffixIconConstraints:\n"
    "                            ReferenceAssetUiScope.maybeOf(context) == null\n"
    "                                ? null\n"
    "                                : const BoxConstraints(\n"
    "                                    minWidth: 38,\n"
    "                                    maxWidth: 64,\n"
    "                                  ),\n"
    "                        contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),",
)

attach_class = """
class _ReferencePromptAttach extends StatelessWidget {
  const _ReferencePromptAttach({required this.selectedPreset});

  final _FactoryPreset? selectedPreset;

  @override
  Widget build(BuildContext context) {
    final scope = ReferenceAssetUiScope.maybeOf(context);
    if (scope == null) {
      return const SizedBox.shrink();
    }

    final target = switch (selectedPreset) {
      _FactoryPreset.web => ReferenceFactoryTarget.web,
      _FactoryPreset.video => ReferenceFactoryTarget.video,
      _FactoryPreset.software => null,
      null => null,
    };
    final tr = context.ilaiosLocale.locale == IlaiosLocale.turkish;
    final tooltip = switch (target) {
      ReferenceFactoryTarget.web =>
        tr ? 'Web referans görsellerini aç' : 'Open Web reference images',
      ReferenceFactoryTarget.video =>
        tr ? 'Video referans görsellerini aç' : 'Open Video reference images',
      null => tr
          ? 'Önce Web Factory veya Video Factory seç'
          : 'Select Web Factory or Video Factory first',
    };
    final enabled = scope.enabled && target != null;
    final count = scope.count;

    return Tooltip(
      message: tooltip,
      child: TextButton(
        key: const Key('prompt-reference-attach'),
        onPressed: enabled
            ? () {
                if (scope.target != target) {
                  scope.onTargetChanged(target);
                }
                if (!scope.open) {
                  scope.onToggle();
                }
              }
            : null,
        style: TextButton.styleFrom(
          minimumSize: const Size(38, 28),
          padding: const EdgeInsets.symmetric(horizontal: 4),
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          visualDensity: VisualDensity.compact,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.attach_file_rounded, size: 15),
            if (count > 0) ...[
              const SizedBox(width: 2),
              Text(
                '$count/20',
                style: const TextStyle(
                  fontSize: 8.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

"""
replace_once(
    create_view,
    "class _FactoryRouteStrip extends StatelessWidget {",
    attach_class + "class _FactoryRouteStrip extends StatelessWidget {",
)

# Context-aware picker labels while retaining existing picker behavior.
replace_once(
    picker_core,
    "import '../../reference_assets/reference_asset_draft.dart';",
    "import '../../reference_assets/reference_asset_draft.dart';\n"
    "import '../../reference_assets/reference_asset_ui_scope.dart';\n"
    "import '../../reference_assets/reference_factory_target.dart';",
)
replace_once(
    picker_core,
    "      final dialogTitle = _text(\n"
    "        'Select Video Factory reference images',\n"
    "        'Video Factory referans görsellerini seç',\n"
    "      ).replaceAll(\"'\", \"''\");",
    "      final dialogTitle = _referenceSelectionTitle(context).replaceAll(\"'\", \"''\");",
)
replace_once(
    picker_core,
    "            'A video can use at most 20 reference images.',\n"
    "            'Bir video en fazla 20 referans görsel kullanabilir.',",
    "            'A request can use at most 20 reference images.',\n"
    "            'Bir istek en fazla 20 referans görsel kullanabilir.',",
)
replace_once(
    picker_core,
    "'${context.tr('videoReferences.title')} ${assets.length}/$maxVideoReferenceAssets'",
    "'${_referenceTitle(context)} ${assets.length}/$maxVideoReferenceAssets'",
)
write(
    picker_core,
    read(picker_core)
    + """

String _referenceTitle(BuildContext context) {
  final target = ReferenceAssetUiScope.maybeOf(context)?.target;
  final tr = context.ilaiosLocale.locale == IlaiosLocale.turkish;
  return switch (target) {
    ReferenceFactoryTarget.web => tr ? 'Web referansları' : 'Web references',
    ReferenceFactoryTarget.video =>
      tr ? 'Video referansları' : 'Video references',
    null => context.tr('videoReferences.title'),
  };
}

String _referenceSelectionTitle(BuildContext context) {
  final target = ReferenceAssetUiScope.maybeOf(context)?.target;
  final tr = context.ilaiosLocale.locale == IlaiosLocale.turkish;
  return switch (target) {
    ReferenceFactoryTarget.web => tr
        ? 'Web Factory referans görsellerini seç'
        : 'Select Web Factory reference images',
    ReferenceFactoryTarget.video => tr
        ? 'Video Factory referans görsellerini seç'
        : 'Select Video Factory reference images',
    null => tr ? 'Referans görsellerini seç' : 'Select reference images',
  };
}
""",
)

# IdentityClient now uses the same shared factory routing.
replace_once(
    identity,
    "import '../reference_assets/reference_asset_draft.dart';",
    "import '../reference_assets/reference_asset_draft.dart';\n"
    "import '../reference_assets/reference_factory_target.dart';",
)
text = read(identity)
text, n = re.subn(
    r"\nbool _isVideoFactoryObjective\(String objective\) \{.*\Z",
    "\n",
    text,
    flags=re.S,
)
if n != 1:
    raise SystemExit(f"IDENTITY_ROUTING_HELPER_REMOVAL expected 1 actual {n}")
text = text.replace("_referenceFactoryCount(", "referenceFactoryCount(")
text = text.replace("_isVideoFactoryObjective(", "isVideoFactoryObjective(")
write(identity, text)

# Explicit 1366/1440/1920 viewport regression.
write(
    "apps/desktop/test/desktop_combined_typography_reference_ux_test.dart",
    """import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_app.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

const _connected = ControlPlaneProjection(
  connected: true,
  status: 'Connected',
  goalCount: 0,
  jobCount: 0,
  lastEvent: null,
  schemaVersion: '1',
);

const _session = DesktopUserSession(
  sessionId: 'session-combined',
  providerId: 'google',
  principalId: 'principal-combined',
  tenantId: 'tenant-combined',
);

Widget _app() => IlaiosDesktopApp(
      key: UniqueKey(),
      projection: _connected,
      userSession: _session,
      onPromptSubmit: (objective) async => const PromptSubmission(
        goalId: 'goal-combined',
        jobId: 'job-combined',
        state: 'PENDING',
      ),
    );

Future<void> _openGoals(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('nav-goals')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'typography uplift and compact Web reference control stay overflow-free at required desktop sizes',
    (tester) async {
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      tester.view.devicePixelRatio = 1;

      for (final size in <Size>[
        const Size(1366, 768),
        const Size(1440, 900),
        const Size(1920, 1080),
      ]) {
        tester.view.physicalSize = size;
        await tester.pumpWidget(_app());
        await tester.pumpAndSettle();

        expect(
          tester.takeException(),
          isNull,
          reason: 'Desktop threw before Goals at ${size.width}x${size.height}',
        );

        final homeNav = find.byKey(const ValueKey('nav-home'));
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
        await tester.tap(find.byKey(const ValueKey('factory-preset-web')));
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('prompt-reference-attach')), findsOneWidget);
        expect(find.byKey(const Key('video-reference-assets')), findsNothing);

        await tester.tap(find.byKey(const Key('prompt-reference-attach')));
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);
        expect(find.text('Web references 0/20'), findsOneWidget);
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Web reference dock overflowed at ${size.width}x${size.height}',
        );
      }
    },
  );

  testWidgets(
    'Video Factory prompt attachment switches the floating dock label',
    (tester) async {
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;

      await tester.pumpWidget(_app());
      await tester.pumpAndSettle();
      await _openGoals(tester);

      await tester.tap(find.byKey(const ValueKey('factory-preset-video')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('prompt-reference-attach')));
      await tester.pumpAndSettle();

      expect(find.text('Video references 0/20'), findsOneWidget);
      expect(find.byKey(const Key('video-reference-add')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}
""",
)

print("COMBINED_PATCH_APPLIED")
