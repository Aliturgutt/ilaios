import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale reaches every primary Desktop surface', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    Future<void> open(String section) async {
      final nav = find.byKey(ValueKey('nav-$section'));
      await tester.ensureVisible(nav);
      await tester.tap(nav);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }

    expect(find.text('İş başlat'), findsOneWidget);
    expect(find.text('Ana Kontrol Merkezi'), findsNothing);

    await open('goals');
    expect(find.text('ILAIOS’un ne oluşturmasını istiyorsun?'), findsOneWidget);

    await open('workflows');
    final workflowsPage = find.byKey(const Key('reference-workflows-page'));
    expect(workflowsPage, findsOneWidget);
    expect(
      find.descendant(of: workflowsPage, matching: find.text('İş Akışları')),
      findsOneWidget,
    );

    await open('agents');
    final agentsPage = find.byKey(const Key('reference-agents-page'));
    expect(agentsPage, findsOneWidget);
    expect(
      find.descendant(of: agentsPage, matching: find.text('Ajanlar')),
      findsOneWidget,
    );

    await open('liveWorkspace');
    expect(find.text('Canlı Çalışma Alanı'), findsWidgets);

    await open('artifacts');
    expect(find.text('Çıktılar'), findsWidgets);

    await open('approvals');
    expect(find.text('Onaylar'), findsWidgets);

    await open('evidence');
    final evidencePage = find.byKey(const Key('reference-evidence-page'));
    expect(evidencePage, findsOneWidget);
    expect(
      find.descendant(of: evidencePage, matching: find.text('Kanıtlar')),
      findsOneWidget,
    );

    await open('costs');
    final costsPage = find.byKey(const Key('reference-costs-page'));
    expect(costsPage, findsOneWidget);
    expect(
      find.descendant(of: costsPage, matching: find.text('Maliyetler')),
      findsOneWidget,
    );

    await open('settings');
    expect(find.text('Ayarlar'), findsWidgets);
    expect(find.text('Dil'), findsWidgets);
  });
}
