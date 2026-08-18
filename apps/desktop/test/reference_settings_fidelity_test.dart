import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Settings keeps the approved dark reference hierarchy', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-settings')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-settings-page')), findsOneWidget);
    expect(find.byKey(const Key('settings-summary-strip')), findsOneWidget);
    expect(find.byKey(const Key('settings-left-navigation')), findsOneWidget);
    expect(find.byKey(const Key('settings-appearance-panel')), findsOneWidget);
    expect(find.byKey(const Key('settings-preview-panel')), findsOneWidget);
    expect(find.byKey(const Key('settings-bottom-grid')), findsOneWidget);
    expect(find.text('Settings'), findsWidgets);
    expect(find.text('Appearance'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Settings renders approved Turkish light surface without fake connectors', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-settings')));
    await tester.pumpAndSettle();

    expect(find.text('Ayarlar'), findsWidgets);
    expect(find.text('Görünüm'), findsWidgets);
    expect(find.text('Çalışma Alanı & Önizleme'), findsOneWidget);
    expect(find.text('GitHub'), findsNothing);
    expect(find.text('OpenAI'), findsNothing);
    expect(find.text('Slack'), findsNothing);
    expect(find.text('AWS'), findsNothing);
    expect(
      find.text('Yetkili entegrasyon telemetrisi kullanılamıyor.'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('Settings shows only authority-derived provider state', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
          schemaVersion: '1',
        ),
        identityProviders: <IdentityProviderOption>[
          IdentityProviderOption(providerId: 'google', displayName: 'Google'),
          IdentityProviderOption(providerId: 'microsoft', displayName: 'Microsoft'),
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

    expect(find.text('Google'), findsOneWidget);
    expect(find.text('Microsoft'), findsOneWidget);
    expect(find.text('Connected'), findsWidgets);
    expect(find.text('GitHub'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
