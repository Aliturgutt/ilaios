import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_app.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

import 'secondary_navigation_test_support.dart';

const _connected = ControlPlaneProjection(
  connected: true,
  status: 'Connected',
  goalCount: 0,
  jobCount: 0,
  lastEvent: null,
  schemaVersion: '1',
);

const _session = DesktopUserSession(
  sessionId: 'session-1',
  providerId: 'google',
  principalId: 'principal-1',
  tenantId: 'tenant-1',
);

void _desktopViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1600, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

IlaiosDesktopApp _app({
  IlaiosLocale locale = IlaiosLocale.english,
  DesktopUserSession? session = _session,
}) =>
    IlaiosDesktopApp(
      projection: _connected,
      locale: locale,
      userSession: session,
      onPromptSubmit: (objective) async => const PromptSubmission(
        goalId: 'goal-1',
        jobId: 'job-1',
        state: 'PENDING',
      ),
    );

Future<void> _openGoals(WidgetTester tester) =>
    openSecondaryDesktopSection(tester, DesktopSection.goals);

void main() {
  testWidgets('V4 removes the global dock and exposes the governed picker inside Goals', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-asset-dock-toggle')), findsNothing);
    expect(find.byKey(const Key('home-prompt-attachments')), findsOneWidget);
    expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);

    await _openGoals(tester);

    expect(find.byKey(const Key('reference-goals-page')), findsOneWidget);
    expect(find.byKey(const Key('goals-composer')), findsOneWidget);
    expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);
    expect(find.byKey(const Key('video-reference-add')), findsOneWidget);
    expect(find.textContaining('20'), findsWidgets);
    expect(find.textContaining('never published as public URLs'), findsOneWidget);
    expect(find.textContaining('free vision provider'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Turkish locale localizes the Goals-integrated reference picker', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app(locale: IlaiosLocale.turkish));
    await tester.pumpAndSettle();
    await _openGoals(tester);

    expect(find.byKey(const Key('reference-asset-dock-toggle')), findsNothing);
    expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);
    expect(find.textContaining('herkese açık URL'), findsOneWidget);
    expect(find.textContaining('ücretsiz görsel sağlayıcısına'), findsOneWidget);
    expect(find.text('Görsel ekle'), findsOneWidget);
  });

  testWidgets('V4 keeps reference assets scoped to Goals even without a session', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app(session: null));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-asset-dock-toggle')), findsNothing);
    await _openGoals(tester);
    expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
