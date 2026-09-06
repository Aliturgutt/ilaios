import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

import 'secondary_navigation_test_support.dart';

void main() {
  testWidgets('Turkish locale reaches every Desktop surface through canonical navigation', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    Future<void> open(DesktopSection section) async {
      if (section == DesktopSection.goals ||
          section == DesktopSection.liveWorkspace ||
          section == DesktopSection.costs) {
        await openSecondaryDesktopSection(tester, section);
      } else {
        final nav = find.byKey(ValueKey('nav-${section.name}'));
        expect(nav, findsOneWidget);
        await tester.ensureVisible(nav);
        await tester.tap(nav);
        await tester.pumpAndSettle();
      }
      expect(tester.takeException(), isNull);
    }

    expect(find.text('İş başlat'), findsOneWidget);
    expect(find.text('Ana Kontrol Merkezi'), findsNothing);

    await open(DesktopSection.goals);
    expect(find.text('ILAIOS’un ne oluşturmasını istiyorsun?'), findsOneWidget);

    await open(DesktopSection.workflows);
    final workflowsPage = find.byKey(const Key('reference-workflows-page'));
    expect(workflowsPage, findsOneWidget);
    expect(
      find.descendant(of: workflowsPage, matching: find.text('İş Akışları')),
      findsOneWidget,
    );

    await open(DesktopSection.agents);
    final agentsPage = find.byKey(const Key('reference-agents-page'));
    expect(agentsPage, findsOneWidget);
    expect(
      find.descendant(of: agentsPage, matching: find.text('Ajanlar')),
      findsOneWidget,
    );

    await open(DesktopSection.liveWorkspace);
    expect(find.text('Canlı Çalışma Alanı'), findsWidgets);

    await open(DesktopSection.artifacts);
    expect(find.text('Çıktılar'), findsWidgets);

    await open(DesktopSection.approvals);
    expect(find.text('Onaylar'), findsWidgets);

    await open(DesktopSection.evidence);
    final evidencePage = find.byKey(const Key('reference-evidence-page'));
    expect(evidencePage, findsOneWidget);
    expect(
      find.descendant(of: evidencePage, matching: find.text('Kanıtlar')),
      findsOneWidget,
    );

    await open(DesktopSection.costs);
    final costsPage = find.byKey(const Key('reference-costs-page'));
    expect(costsPage, findsOneWidget);
    expect(
      find.descendant(of: costsPage, matching: find.text('Maliyetler')),
      findsOneWidget,
    );

    await open(DesktopSection.settings);
    expect(find.text('Ayarlar'), findsWidgets);
    expect(find.text('Dil'), findsWidgets);
  });
}
