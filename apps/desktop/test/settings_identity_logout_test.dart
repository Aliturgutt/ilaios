import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Settings connected provider invokes canonical logout callback', (
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
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-settings')));
    await tester.pumpAndSettle();

    final action = find.byKey(
      const ValueKey('settings-provider-connect-google'),
    );
    expect(action, findsOneWidget);
    final button = tester.widget<OutlinedButton>(action);
    expect(button.onPressed, isNotNull);
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
        userSession: DesktopUserSession(
          sessionId: 'session-1',
          providerId: 'google',
          principalId: 'principal-1',
          tenantId: 'tenant-1',
          displayIdentity: 'user@example.test',
        ),
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
}
