import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('top account uses the existing Google sign-in callback when signed out', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    String? providerId;
    await tester.pumpWidget(
      IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
        identityProviders: const [
          IdentityProviderOption(providerId: 'google', displayName: 'Google'),
        ],
        onSignIn: (value) async => providerId = value,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('top-account-google-sign-in')), findsOneWidget);
    expect(find.text('Google ile giriş'), findsOneWidget);

    await tester.tap(find.byKey(const Key('top-account-google-sign-in')));
    await tester.pump();
    expect(providerId, 'google');
  });

  testWidgets('Home starts with three compact attachment actions and no open picker', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-add-document')), findsOneWidget);
    expect(find.byKey(const Key('home-add-image')), findsOneWidget);
    expect(find.byKey(const Key('home-add-video')), findsOneWidget);
    expect(find.text('Dosya Ekle'), findsOneWidget);
    expect(find.text('Görsel Ekle'), findsOneWidget);
    expect(find.text('Video Ekle'), findsOneWidget);
    expect(find.byKey(const Key('home-attachment-pane-documents')), findsNothing);
    expect(find.byKey(const Key('home-attachment-pane-images')), findsNothing);
    expect(find.byKey(const Key('home-attachment-pane-video')), findsNothing);
  });

  testWidgets('Home exposes exactly the nine canonical factory families', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1300));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.english,
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-canonical-factory-grid')), findsOneWidget);
    for (var index = 1; index <= 9; index++) {
      expect(find.byKey(ValueKey('home-factory-$index')), findsOneWidget);
    }
    expect(find.text('Web Factory'), findsOneWidget);
    expect(find.text('Video / Media Factory'), findsOneWidget);
    expect(find.text('Software Factory'), findsOneWidget);
    expect(find.text('App Factory'), findsOneWidget);
    expect(find.text('Research / Data Factory'), findsOneWidget);
    expect(find.text('Security Factory'), findsOneWidget);
    expect(find.text('Creative / Document Factory'), findsOneWidget);
    expect(find.text('Commerce / Growth Factory'), findsOneWidget);
    expect(find.text('Personal Operations Factory'), findsOneWidget);
  });

  testWidgets('brand field uses seamless canonical Carbon and White surfaces', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(themeMode: ThemeMode.dark),
    );
    await tester.pumpAndSettle();

    var brand = tester.widget<Container>(
      find.byKey(const Key('reference-brand-lockup-v9')),
    );
    expect(brand.color, const Color(0xFF0A0A0A));
    expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);

    await tester.pumpWidget(
      const IlaiosDesktopApp(themeMode: ThemeMode.light),
    );
    await tester.pumpAndSettle();

    brand = tester.widget<Container>(
      find.byKey(const Key('reference-brand-lockup-v9')),
    );
    expect(brand.color, const Color(0xFFFFFFFF));
    expect(find.byKey(const Key('reference-brand-horizontal-light')), findsOneWidget);
  });

  testWidgets('Turkish shell does not leak the raw English control-plane error', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        operationalStatus: 'Control plane is unreachable',
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Control plane is unreachable'), findsNothing);
  });
}
