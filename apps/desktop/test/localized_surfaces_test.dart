import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale reaches all seven canonical Desktop surfaces', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    Future<void> open(DesktopSection section) async {
      final nav = find.byKey(ValueKey('nav-${section.name}'));
      expect(nav, findsOneWidget);
      await tester.ensureVisible(nav);
      await tester.tap(nav);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }

    expect(find.text('İş başlat'), findsOneWidget);
    expect(find.text('Ana Kontrol Merkezi'), findsNothing);
    expect(find.byKey(const Key('reference-secondary-navigation')), findsNothing);

    await open(DesktopSection.workflows);
    expect(find.byKey(const Key('reference-workflows-page')), findsOneWidget);
    expect(find.text('İş Akışları'), findsWidgets);

    await open(DesktopSection.agents);
    expect(find.byKey(const Key('reference-agents-page')), findsOneWidget);
    expect(find.text('Ajanlar'), findsWidgets);

    await open(DesktopSection.artifacts);
    expect(find.text('Çıktılar'), findsWidgets);

    await open(DesktopSection.approvals);
    expect(find.text('Onaylar'), findsWidgets);

    await open(DesktopSection.evidence);
    expect(find.byKey(const Key('reference-evidence-page')), findsOneWidget);
    expect(find.text('Kanıtlar'), findsWidgets);

    await open(DesktopSection.settings);
    expect(find.text('Ayarlar'), findsWidgets);
    expect(find.text('Dil'), findsWidgets);

    for (final legacy in <DesktopSection>[
      DesktopSection.goals,
      DesktopSection.liveWorkspace,
      DesktopSection.costs,
    ]) {
      expect(find.byKey(ValueKey('nav-${legacy.name}')), findsNothing);
    }
  });
}
