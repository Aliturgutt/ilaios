import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

import 'secondary_navigation_test_support.dart';

void main() {
  Future<void> pumpTurkish(WidgetTester tester, {OperationalSnapshot? snapshot}) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
        operationalSnapshot: snapshot ?? const OperationalSnapshot.unavailable(),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('Workflows exposes five distinct summary cards', (tester) async {
    await pumpTurkish(tester);
    await tester.tap(find.byKey(const ValueKey('nav-workflows')));
    await tester.pumpAndSettle();

    for (final id in const ['total', 'active', 'approval', 'overdue', 'completed']) {
      expect(find.byKey(ValueKey('workflows-summary-$id')), findsOneWidget);
    }
  });

  testWidgets('Agents exposes four distinct authoritative summary cards', (tester) async {
    await pumpTurkish(tester);
    await tester.tap(find.byKey(const ValueKey('nav-agents')));
    await tester.pumpAndSettle();

    for (final id in const ['total', 'active', 'busy', 'idle']) {
      expect(find.byKey(ValueKey('agents-summary-$id')), findsOneWidget);
    }
  });

  testWidgets('Approvals empty queue does not reserve an empty detail rail', (tester) async {
    await pumpTurkish(tester);
    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('approvals-table')), findsOneWidget);
    expect(find.byKey(const Key('approvals-right-rail')), findsNothing);
  });

  testWidgets('Evidence exposes search and compact filter controls', (tester) async {
    await pumpTurkish(tester);
    await tester.tap(find.byKey(const ValueKey('nav-evidence')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('evidence-search')), findsOneWidget);
    expect(find.byKey(const Key('evidence-filter')), findsOneWidget);
  });

  testWidgets('secondary surfaces remain reachable after seven-primary navigation repair', (
    tester,
  ) async {
    await pumpTurkish(tester);
    for (final section in const [
      DesktopSection.goals,
      DesktopSection.liveWorkspace,
      DesktopSection.costs,
    ]) {
      await openSecondaryDesktopSection(tester, section);
      expect(tester.takeException(), isNull);
    }
  });
}
