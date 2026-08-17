import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('1536x1024 wide home renders the approved reference hierarchy', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-workflow-strip')), findsOneWidget);
    expect(find.byKey(const Key('reference-agent-row')), findsOneWidget);
    expect(find.byKey(const Key('reference-workspace')), findsOneWidget);
    expect(find.byKey(const Key('reference-artifacts-panel')), findsOneWidget);
    expect(find.byKey(const Key('reference-evidence-panel')), findsOneWidget);
    expect(find.byKey(const Key('reference-status-card')), findsOneWidget);
    expect(find.byKey(const Key('reference-latest-logs')), findsOneWidget);
    expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);

    for (final stage in <String>[
      'Goal Intake',
      'Planning',
      'Execution',
      'Verification',
      'Delivery',
    ]) {
      expect(find.text(stage), findsOneWidget);
    }

    for (final role in <String>[
      'Architect Agent',
      'Frontend Dev',
      'Backend Dev',
      'Test Engineer',
      'Security Agent',
      'Browser Agent',
      'Deploy Agent',
    ]) {
      expect(find.text(role), findsOneWidget);
    }

    expect(find.text('Live Code'), findsWidgets);
    expect(find.text('Terminal'), findsWidgets);
    expect(find.text('Browser'), findsWidgets);
    expect(find.text('Files'), findsOneWidget);
    expect(find.text('Logs'), findsOneWidget);
    expect(find.text('Events'), findsWidgets);
    expect(find.text('LATEST ARTIFACTS'), findsOneWidget);
    expect(find.text('EVIDENCE & VERIFICATION'), findsOneWidget);
    expect(find.text('STATUS'), findsOneWidget);
    expect(find.text('COST & USAGE'), findsOneWidget);
    expect(find.text('APPROVALS'), findsOneWidget);
    expect(find.text('LATEST LOGS'), findsOneWidget);

    expect(find.text('73%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.text('7 / 25'), findsNothing);
    expect(find.text('2.4M / 20M'), findsNothing);
  });

  testWidgets(
    'DPI-compressed 1320x720 desktop keeps the full reference in one viewport',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1320, 720));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(const IlaiosDesktopApp());
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(
        find.byKey(const Key('reference-dpi-scaled-viewport')),
        findsOneWidget,
      );
      expect(find.byKey(const Key('reference-desktop-sidebar-v5')), findsOneWidget);
      expect(find.byKey(const Key('reference-workflow-strip')), findsOneWidget);
      expect(find.byKey(const Key('reference-agent-row')), findsOneWidget);
      expect(find.byKey(const Key('reference-workspace')), findsOneWidget);
      expect(find.byKey(const Key('reference-artifacts-panel')), findsOneWidget);
      expect(find.byKey(const Key('reference-evidence-panel')), findsOneWidget);
      expect(find.byKey(const Key('reference-status-card')), findsOneWidget);
      expect(find.byKey(const Key('reference-latest-logs')), findsOneWidget);
      expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);

      final workspace = tester.getRect(
        find.byKey(const Key('reference-workspace')),
      );
      final artifacts = tester.getRect(
        find.byKey(const Key('reference-artifacts-panel')),
      );
      final bottomStatus = tester.getRect(
        find.byKey(const Key('reference-bottom-status-v2')),
      );

      expect(workspace.top, lessThan(artifacts.top));
      expect(artifacts.bottom, lessThanOrEqualTo(bottomStatus.top + 1));
      expect(bottomStatus.bottom, lessThanOrEqualTo(720));

      await tester.tap(
        find.byKey(const ValueKey('workspace-tab-terminal')),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('reference hierarchy remains localized in Turkish', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Aktif İş Akışı'), findsOneWidget);
    expect(find.text('Hedef Alımı'), findsOneWidget);
    expect(find.text('Planlama'), findsOneWidget);
    expect(find.text('Yürütme'), findsOneWidget);
    expect(find.text('Doğrulama'), findsOneWidget);
    expect(find.text('Teslimat'), findsOneWidget);
    expect(find.text('Genel İlerleme'), findsOneWidget);
    expect(find.text('CANLI YÜRÜTME'), findsOneWidget);
    expect(find.text('CANLI ÇALIŞMA ALANI'), findsOneWidget);
    expect(find.text('Canlı Kod'), findsWidgets);
    expect(find.text('DURUM'), findsOneWidget);
    expect(find.text('MALİYET VE KULLANIM'), findsOneWidget);
    expect(find.text('ONAYLAR'), findsOneWidget);
    expect(find.text('SON GÜNLÜKLER'), findsOneWidget);
    expect(find.text('73%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });
}
