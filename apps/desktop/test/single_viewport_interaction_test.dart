import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('1536x1024 canonical Home remains scroll-safe and bounded', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(
      find.byKey(const Key('command-center-short-viewport-scroll')),
      findsOneWidget,
    );
    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    final bottomBar = find.byKey(const Key('reference-bottom-status-v2'));
    expect(bottomBar, findsOneWidget);
    expect(tester.getBottomRight(bottomBar).dy, lessThanOrEqualTo(1024));
  });

  testWidgets('canonical Home controls are real bounded interactive controls', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    expect(find.text('View all agents'), findsOneWidget);
    expect(find.byKey(const Key('home-templates')), findsNothing);
    expect(find.byKey(const Key('home-last-session')), findsNothing);
    expect(find.byKey(const Key('home-assign-agent')), findsNothing);
    expect(find.byKey(const Key('home-factory-video')), findsNothing);

    final viewAll = find.text('View all agents');
    await tester.ensureVisible(viewAll);
    await tester.tap(viewAll);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('reference-agents-page')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Home prompt is submitted through the authenticated execution callback', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    String? submittedObjective;
    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
        ),
        onPromptSubmit: (objective) async {
          submittedObjective = objective;
          return const PromptSubmission(
            goalId: 'goal-home-1',
            jobId: 'job-home-1',
            state: 'created',
          );
        },
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('home-command-prompt')),
      'Build a verified website from the Home command center.',
    );
    await tester.pump();
    final submit = find.byKey(const Key('home-new-work'));
    await tester.ensureVisible(submit);
    final button = tester.widget<FilledButton>(submit);
    expect(button.onPressed, isNotNull);
    await tester.tap(submit);
    await tester.pumpAndSettle();

    expect(
      submittedObjective,
      'Build a verified website from the Home command center.',
    );
    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
