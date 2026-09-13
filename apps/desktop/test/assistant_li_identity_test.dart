import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/features/assistant/assistant_symbol.dart';
import 'package:ilaios_desktop/features/li/li_view.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

const _founder = DesktopUserSession(
  sessionId: 'session-founder',
  providerId: 'google',
  principalId: 'usr_founder',
  tenantId: 'tnt_founder',
  liFounder: true,
);
const _customer = DesktopUserSession(
  sessionId: 'session-customer',
  providerId: 'google',
  principalId: 'usr_customer_owner',
  tenantId: 'tnt_customer',
);
const _state = DesktopLiState(
  name: 'Li',
  founderOperator: true,
  userId: 'usr_founder',
  tenantId: 'tnt_founder',
  source: 'canonical_desktop_session',
);

Widget _app({
  DesktopUserSession? session = _founder,
  IlaiosLocale locale = IlaiosLocale.english,
  Brightness brightness = Brightness.light,
  Future<DesktopLiState> Function()? state,
  Future<List<DesktopLiMemory>> Function()? memories,
  Future<DesktopLiMemory> Function(String, String)? remember,
}) =>
    MaterialApp(
      theme: ThemeData(brightness: brightness),
      home: IlaiosLocaleScope(
        locale: locale,
        onChanged: (_) {},
        child: Scaffold(
          body: LiView(
            userSession: session,
            onFetchState: state ?? () async => _state,
            onFetchMemories: memories ?? () async => [],
            onRemember: remember,
          ),
        ),
      ),
    );

void main() {
  for (final locale in IlaiosLocale.values) {
    for (final brightness in Brightness.values) {
      testWidgets('authorized panel identity $locale $brightness', (tester) async {
        await tester.pumpWidget(_app(locale: locale, brightness: brightness));
        await tester.pumpAndSettle();
        expect(find.text('Li — Founder Intelligence'), findsOneWidget);
        final image = tester.widget<Image>(
          find.descendant(of: find.byType(AssistantSymbol), matching: find.byType(Image)),
        );
        expect((image.image as AssetImage).assetName,
            brightness == Brightness.dark
                ? '../../brand/assets/05-ilaios-app-icon.jpg'
                : '../../brand/assets/04-ilaios-symbol-light.jpg');
        expect(image.fit, BoxFit.contain);
        expect(image.color, isNull);
        expect(tester.takeException(), isNull);
      });
    }
  }

  testWidgets('runtime theme switch updates the canonical symbol', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();
    await tester.pumpWidget(_app(brightness: Brightness.dark));
    await tester.pumpAndSettle();
    final image = tester.widget<Image>(
      find.descendant(of: find.byType(AssistantSymbol), matching: find.byType(Image)),
    );
    expect((image.image as AssetImage).assetName,
        '../../brand/assets/05-ilaios-app-icon.jpg');
    expect(tester.takeException(), isNull);
  });

  for (final session in <DesktopUserSession?>[null, _customer]) {
    testWidgets('non-founder never loads or renders Li: ${session?.sessionId}',
        (tester) async {
      var calls = 0;
      await tester.pumpWidget(_app(
        session: session,
        state: () async { calls++; return _state; },
        memories: () async { calls++; return []; },
      ));
      await tester.pumpAndSettle();
      expect(calls, 0);
      expect(find.textContaining('Li'), findsNothing);
      expect(find.byType(AssistantSymbol), findsNothing);
      expect(find.byKey(const Key('li-memory-composer')), findsNothing);
    });
  }

  testWidgets('founder memory waits for matching server state', (tester) async {
    final pending = Completer<DesktopLiState>();
    var reads = 0;
    await tester.pumpWidget(_app(
      state: () => pending.future,
      memories: () async { reads++; return []; },
    ));
    await tester.pump();
    expect(reads, 0);
    expect(find.byType(AssistantSymbol), findsNothing);
    pending.complete(_state);
    await tester.pumpAndSettle();
    expect(reads, 1);
    expect(find.text('Li — Founder Intelligence'), findsOneWidget);
  });

  for (final invalid in <DesktopLiState>[
    const DesktopLiState(name: 'Li', founderOperator: false,
        userId: 'usr_founder', tenantId: 'tnt_founder', source: 'canonical_desktop_session'),
    const DesktopLiState(name: 'Li', founderOperator: true,
        userId: 'other', tenantId: 'tnt_founder', source: 'canonical_desktop_session'),
    const DesktopLiState(name: 'Li', founderOperator: true,
        userId: 'usr_founder', tenantId: 'other', source: 'canonical_desktop_session'),
    const DesktopLiState(name: 'Li', founderOperator: true,
        userId: 'usr_founder', tenantId: 'tnt_founder', source: 'client'),
  ]) {
    testWidgets('mismatched founder state blocks memory: '
        '${invalid.founderOperator}/${invalid.userId}/${invalid.tenantId}/${invalid.source}',
        (tester) async {
      var reads = 0;
      await tester.pumpWidget(_app(
        state: () async => invalid,
        memories: () async { reads++; return []; },
      ));
      await tester.pumpAndSettle();
      expect(reads, 0);
      expect(find.text('Li — Founder Intelligence'), findsNothing);
      expect(find.byKey(const Key('li-memory-composer')), findsNothing);
      expect(find.text('Access could not be verified.'), findsOneWidget);
    });
  }

  testWidgets('logout rejects a late founder response before reading memory',
      (tester) async {
    final pending = Completer<DesktopLiState>();
    var reads = 0;
    await tester.pumpWidget(_app(
      state: () => pending.future,
      memories: () async { reads++; return []; },
    ));
    await tester.pump();
    await tester.pumpWidget(_app(session: null));
    pending.complete(_state);
    await tester.pumpAndSettle();
    expect(reads, 0);
    expect(find.textContaining('Li'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('save errors stay private and localize on locale change', (tester) async {
    Future<DesktopLiMemory> fail(String kind, String content) async =>
        throw StateError('private-provider-credential');
    await tester.pumpWidget(_app(remember: fail));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('li-memory-content')), 'Remember this');
    await tester.ensureVisible(find.byKey(const Key('li-memory-save')));
    await tester.tap(find.byKey(const Key('li-memory-save')));
    await tester.pumpAndSettle();
    expect(find.text('Could not save memory.'), findsOneWidget);
    expect(find.textContaining('private-provider-credential'), findsNothing);
    await tester.pumpWidget(_app(remember: fail, locale: IlaiosLocale.turkish));
    await tester.pumpAndSettle();
    expect(find.text('Hafıza kaydedilemedi.'), findsOneWidget);
    expect(find.textContaining('private-provider-credential'), findsNothing);
  });

  testWidgets('a late save cannot restore founder UI after logout', (tester) async {
    final pending = Completer<DesktopLiMemory>();
    var reads = 0;
    await tester.pumpWidget(_app(
      memories: () async { reads++; return []; },
      remember: (_, _) => pending.future,
    ));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('li-memory-content')), 'Private draft');
    await tester.ensureVisible(find.byKey(const Key('li-memory-save')));
    await tester.tap(find.byKey(const Key('li-memory-save')));
    await tester.pump();
    await tester.pumpWidget(_app(session: _customer));
    pending.complete(DesktopLiMemory(
      memoryId: 'memory', kind: 'working', content: 'Private draft',
      source: 'founder', confidence: 1, sensitivity: 'private',
      createdAt: DateTime.utc(2026, 9, 13),
    ));
    await tester.pumpAndSettle();
    expect(reads, 1);
    expect(find.textContaining('Private draft'), findsNothing);
    expect(find.textContaining('Li'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
