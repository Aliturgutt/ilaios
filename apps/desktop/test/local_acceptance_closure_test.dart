import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/dashboard/reference_home_dashboard_v3.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/main.dart';

class _RecordingTransport implements ControlPlaneTransport {
  final List<({String method, Uri uri, Map<String, String> headers, String? body})>
      requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'GET', uri: uri, headers: Map.of(headers), body: null));
    return const ControlPlaneResponse(statusCode: 200, body: '{}');
  }

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'POST', uri: uri, headers: Map.of(headers), body: body));
    return const ControlPlaneResponse(statusCode: 200, body: '{}');
  }
}

const _session = DesktopUserSession(
  sessionId: 'session-local-acceptance',
  providerId: 'google',
  principalId: 'principal-1',
  tenantId: 'tenant-1',
  displayIdentity: 'user@example.test',
);

void main() {
  test('canonical logout revokes broker session before UI may clear it', () async {
    final transport = _RecordingTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );

    await client.logout(_session);

    expect(transport.requests, hasLength(1));
    final request = transport.requests.single;
    expect(request.method, 'POST');
    expect(request.uri.path, '/v1/auth/logout');
    expect(
      jsonDecode(request.body!),
      <String, Object?>{'session_id': 'session-local-acceptance'},
    );
    expect(request.headers['Authorization'], 'Bearer local-transport-token');
  });

  testWidgets('Settings connected Google exposes canonical sign-out callback', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    var logoutCalls = 0;

    await tester.pumpWidget(
      IlaiosDesktopApp(
        identityProviders: const <IdentityProviderOption>[
          IdentityProviderOption(providerId: 'google', displayName: 'Google'),
        ],
        userSession: _session,
        identityStatus: 'Authenticated',
        onLogout: () async => logoutCalls += 1,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-settings')));
    await tester.pumpAndSettle();

    final action = find.byKey(
      const ValueKey('settings-provider-connect-google'),
    );
    expect(action, findsOneWidget);
    expect(tester.widget<OutlinedButton>(action).onPressed, isNotNull);
    expect(find.text('Sign out'), findsWidgets);

    await tester.tap(action);
    await tester.pumpAndSettle();
    expect(logoutCalls, 1);
    expect(find.byKey(const Key('settings-provider-error')), findsNothing);
  });

  testWidgets('Settings connected provider fails closed without logout callback', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        identityProviders: <IdentityProviderOption>[
          IdentityProviderOption(providerId: 'google', displayName: 'Google'),
        ],
        userSession: _session,
        identityStatus: 'Authenticated',
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-settings')));
    await tester.pumpAndSettle();

    final action = find.byKey(
      const ValueKey('settings-provider-connect-google'),
    );
    expect(action, findsOneWidget);
    expect(tester.widget<OutlinedButton>(action).onPressed, isNull);
  });

  testWidgets('Home Offline metric stays within bounded KPI typography', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          home: Scaffold(
            body: ReferenceHomeDashboardV3(
              projection: const ControlPlaneProjection.unavailable(),
              snapshot: const OperationalSnapshot.unavailable(),
              status: 'Operational APIs not connected',
              onNavigate: (_) {},
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    final offline = find.text('Offline');
    expect(offline, findsOneWidget);
    final text = tester.widget<Text>(offline);
    expect(text.style?.fontSize, isNotNull);
    expect(text.style!.fontSize!, lessThanOrEqualTo(17));
    expect(tester.takeException(), isNull);
  });

  test('portable/install launch contract is executable-relative and shell-independent', () {
    final runtimeSource = File('lib/control_plane/local_runtime.dart').readAsStringSync();
    final packageSource = File('../../tools/desktop/verify_and_package_combined.ps1')
        .readAsStringSync();

    expect(runtimeSource, contains('File(Platform.resolvedExecutable).parent'));
    expect(runtimeSource, contains("\\\\ilaios_control_plane.exe"));
    expect(packageSource, contains(r'$shortcut.WorkingDirectory = $WorkingDirectory'));
    expect(
      packageSource,
      contains(
        r'Start-Process -FilePath $installedExe -WorkingDirectory $installRoot -PassThru',
      ),
    );
    expect(packageSource, isNot(contains('Wait-Process')));
  });
}
