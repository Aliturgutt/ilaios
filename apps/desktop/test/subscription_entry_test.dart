import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/features/operations/subscription_entry.dart';

void main() {
  for (final locale in IlaiosLocale.values) {
    testWidgets('subscription opens canonical account surface in ${locale.code}',
        (tester) async {
      Uri? opened;
      await tester.pumpWidget(IlaiosLocaleScope(
        locale: locale,
        onChanged: (_) {},
        child: MaterialApp(home: Scaffold(body: SubscriptionEntry(
          opener: (uri) async { opened = uri; },
        ))),
      ));
      await tester.tap(find.byKey(const Key('subscription-entry')));
      await tester.pumpAndSettle();
      expect(opened?.scheme, 'https');
      expect(opened?.host, 'app.ilaios.com');
      expect(opened?.path, '/subscription');
      expect(opened?.queryParameters, {'lang': locale.code});
      expect(opened?.userInfo, isEmpty);
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('launcher failure leaves a usable recovery message', (tester) async {
    await tester.pumpWidget(IlaiosLocaleScope(
      locale: IlaiosLocale.turkish,
      onChanged: (_) {},
      child: MaterialApp(home: Scaffold(body: SubscriptionEntry(
        opener: (_) async { throw StateError('unavailable'); },
      ))),
    ));
    await tester.tap(find.byKey(const Key('subscription-entry')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Abonelik sayfası açılamadı'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
