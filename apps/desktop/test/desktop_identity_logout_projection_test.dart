import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/features/dashboard/reference_desktop_shell_v11.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  testWidgets('authenticated Desktop exposes the canonical logout callback', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    var logoutCalls = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ReferenceDesktopShellV11(
            projection: const ControlPlaneProjection.unavailable(),
            operationalSnapshot: const OperationalSnapshot.unavailable(),
            operationalStatus: 'connected',
            identityProviders: const <IdentityProviderOption>[
              IdentityProviderOption(providerId: 'google', displayName: 'Google'),
            ],
            userSession: const DesktopUserSession(
              sessionId: 'session-1',
              providerId: 'google',
              principalId: 'principal-1',
              tenantId: 'tenant-1',
              displayIdentity: 'user@example.test',
            ),
            identityStatus: 'Authenticated',
            onLogout: () async => logoutCalls += 1,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final logout = find.byKey(const Key('desktop-identity-logout'));
    expect(logout, findsOneWidget);
    await tester.tap(logout);
    await tester.pumpAndSettle();
    expect(logoutCalls, 1);
  });

  testWidgets('signed-out Desktop does not expose logout', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ReferenceDesktopShellV11(
            projection: ControlPlaneProjection.unavailable(),
            operationalSnapshot: OperationalSnapshot.unavailable(),
            operationalStatus: 'connected',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('desktop-identity-logout')), findsNothing);
  });
}
