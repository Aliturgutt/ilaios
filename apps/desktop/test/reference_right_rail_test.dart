import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('V4 Home removes the permanent right rail and keeps status in sidebar', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('command-center-session')), findsNothing);
    expect(find.byKey(const Key('command-center-activities')), findsNothing);
    expect(find.byKey(const Key('command-center-alerts')), findsNothing);

    final hero = find.byKey(const Key('command-center-hero'));
    final attention = find.byKey(const Key('command-center-attention'));
    final completed = find.byKey(const Key('command-center-completed'));
    final sidebar = find.byKey(const Key('reference-desktop-sidebar-v5'));
    final status = find.byKey(const Key('reference-bottom-status-v2'));
    final scroll = find.byKey(const Key('command-center-short-viewport-scroll'));
    expect(hero, findsOneWidget);
    expect(attention, findsOneWidget);
    expect(completed, findsOneWidget);
    expect(sidebar, findsOneWidget);
    expect(status, findsOneWidget);
    expect(
      find.descendant(of: sidebar, matching: status),
      findsOneWidget,
    );
    expect(scroll, findsOneWidget);
    expect(tester.getTopLeft(hero).dy, greaterThanOrEqualTo(60));

    final statusTopBeforeScroll = tester.getTopLeft(status).dy;
    final statusLeftBeforeScroll = tester.getTopLeft(status).dx;
    await tester.drag(scroll, const Offset(0, -1600));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(tester.getTopLeft(status).dy, statusTopBeforeScroll);
    expect(tester.getTopLeft(status).dx, statusLeftBeforeScroll);
    expect(
      tester.getBottomRight(status).dy,
      lessThanOrEqualTo(tester.getBottomRight(sidebar).dy),
    );
  });
}
