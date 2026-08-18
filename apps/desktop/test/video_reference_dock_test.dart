import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_app.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
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

void main() {
  testWidgets('authenticated Desktop exposes the shared Web Video reference dock', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    final toggle = find.byKey(const Key('reference-asset-dock-toggle'));
    expect(toggle, findsOneWidget);
    expect(find.text('Reference images'), findsOneWidget);
    expect(find.byKey(const Key('video-reference-assets')), findsNothing);

    await tester.tap(toggle);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);
    expect(find.byKey(const Key('video-reference-add')), findsOneWidget);
    expect(find.textContaining('20'), findsWidgets);
    expect(find.textContaining('not published as public URLs'), findsOneWidget);
    expect(find.textContaining('free vision provider'), findsOneWidget);
  });

  testWidgets('Turkish locale localizes shared reference dock and privacy disclosure', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app(locale: IlaiosLocale.turkish));
    await tester.pumpAndSettle();

    final toggle = find.byKey(const Key('reference-asset-dock-toggle'));
    expect(find.text('Referans görseller'), findsOneWidget);
    await tester.tap(toggle);
    await tester.pumpAndSettle();

    expect(find.textContaining('herkese açık URL'), findsOneWidget);
    expect(find.textContaining('ücretsiz görsel sağlayıcısına'), findsOneWidget);
    expect(find.text('Görsel ekle'), findsOneWidget);
  });

  testWidgets('shared reference dock remains disabled without an authenticated session', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app(session: null));
    await tester.pumpAndSettle();

    final button = tester.widget<FilledButton>(
      find.byKey(const Key('reference-asset-dock-toggle')),
    );
    expect(button.onPressed, isNull);
  });
}
