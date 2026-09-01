import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  Future<void> openGoals(WidgetTester tester) async {
    await tester.tap(find.byKey(const ValueKey('nav-goals')));
    await tester.pumpAndSettle();
  }

  testWidgets('Goals keeps the V4 desktop hierarchy without screenshot telemetry',
      (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 12,
          jobCount: 7,
          lastEvent: 'goal.updated',
          schemaVersion: '1',
        ),
      ),
    );
    await tester.pumpAndSettle();
    await openGoals(tester);

    expect(find.byKey(const Key('reference-goals-page')), findsOneWidget);
    expect(find.byKey(const Key('goals-composer')), findsOneWidget);
    expect(find.byKey(const Key('goals-kpis')), findsOneWidget);
    expect(find.byKey(const Key('goals-tabs')), findsOneWidget);
    expect(find.byKey(const Key('goals-table')), findsOneWidget);
    expect(find.byKey(const Key('goals-selected')), findsNothing);
    expect(find.byKey(const Key('goals-distribution')), findsNothing);
    expect(find.text('12'), findsWidgets);
    expect(find.text('68%'), findsNothing);
    expect(find.text('Website Launch'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Goals renders the V4 Turkish light surface',
      (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();
    await openGoals(tester);

    expect(find.text('Hedefler'), findsWidgets);
    expect(find.byKey(const Key('goals-composer')), findsOneWidget);
    expect(find.byKey(const Key('goals-kpis')), findsNothing);
    expect(find.byKey(const Key('business-capability-selector')), findsOneWidget);
    expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);
    expect(find.text('Dışa Aktar'), findsNothing);
    expect(find.text('Yeni Hedef'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Goals remains one viewport at compact desktop size',
      (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1180, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp(locale: IlaiosLocale.turkish));
    await tester.pumpAndSettle();
    await openGoals(tester);

    expect(find.byKey(const Key('reference-goals-page')), findsOneWidget);
    expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsNothing);
    expect(find.byKey(const Key('goals-content-scroll')), findsOneWidget);
    await tester.drag(
      find.byKey(const Key('goals-content-scroll')),
      const Offset(0, -480),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('goals-table')), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('goals-table')));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
