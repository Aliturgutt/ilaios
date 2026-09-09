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
  testWidgets('canonical Home exposes governed source-video picker in a compact dialog', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-prompt-attachments')), findsOneWidget);
    expect(find.byKey(const Key('home-add-video')), findsOneWidget);
    expect(find.byKey(const Key('source-video-picker')), findsNothing);

    await tester.tap(find.byKey(const Key('home-add-video')));
    await tester.pumpAndSettle();
    expect(find.text('Add video'), findsWidgets);
    expect(find.byKey(const Key('source-video-picker')), findsOneWidget);
    expect(find.byKey(const Key('source-video-add')), findsOneWidget);
    expect(find.byKey(const Key('reference-secondary-navigation')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Turkish canonical Home localizes the governed attachment controls', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app(locale: IlaiosLocale.turkish));
    await tester.pumpAndSettle();

    expect(find.text('Dosya ekle'), findsOneWidget);
    expect(find.text('Görsel ekle'), findsOneWidget);
    expect(find.text('Video ekle'), findsOneWidget);
    await tester.tap(find.byKey(const Key('home-add-video')));
    await tester.pumpAndSettle();
    expect(find.text('Video ekle'), findsWidgets);
    expect(find.byKey(const Key('source-video-picker')), findsOneWidget);
  });

  testWidgets('local attachment staging stays available before sign-in while submit remains governed', (
    tester,
  ) async {
    _desktopViewport(tester);
    await tester.pumpWidget(_app(session: null));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-prompt-attachments')), findsOneWidget);
    for (final key in const [
      Key('home-add-document'),
      Key('home-add-image'),
      Key('home-add-video'),
    ]) {
      final button = tester.widget<OutlinedButton>(find.byKey(key));
      expect(button.onPressed, isNotNull);
    }

    await tester.tap(find.byKey(const Key('home-add-document')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('company-knowledge-picker')), findsOneWidget);
    await tester.tap(find.text('Close'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('home-add-image')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('reference-asset-picker')), findsOneWidget);
    await tester.tap(find.text('Close'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('home-add-video')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('source-video-picker')), findsOneWidget);

    expect(tester.takeException(), isNull);
  });
}
