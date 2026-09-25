import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/li/li_web_bridge.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  DesktopUserSession session({bool founder = true}) => DesktopUserSession(
    sessionId: 'session',
    providerId: 'google',
    principalId: 'user',
    tenantId: 'tenant',
    liFounder: founder,
  );
  DesktopLiState founderState({String user = 'user'}) => DesktopLiState(
    name: 'Li',
    founderOperator: true,
    userId: user,
    tenantId: 'tenant',
    source: 'canonical_desktop_session',
  );
  Map<String, dynamic> binding(String persona) => {
    'user_id': 'user',
    'tenant_id': 'tenant',
    'project_id': null,
    'workload_id': null,
    'persona': persona,
  };
  String command(String operation, [Map<String, Object?> args = const {}]) =>
      jsonEncode({'id': '1', 'operation': operation, 'args': args});

  test('non-founder is denied before any service call', () async {
    var called = 0;
    final bridge = LiWebBridge(
      session: session(founder: false),
      isSessionActive: () => true,
      verifyFounder: () async {
        called++;
        return founderState();
      },
      request: (_) async {
        called++;
        return {};
      },
      fetchMemories: () async {
        called++;
        return [];
      },
      remember: (_, _) async {
        called++;
        throw StateError('unexpected');
      },
    );
    expect((await bridge.handle(command('list')))['ok'], false);
    expect((await bridge.handle(command('memories')))['ok'], false);
    expect(called, 0);
  });

  test('mismatched founder state is rejected', () async {
    var called = 0;
    final bridge = LiWebBridge(
      session: session(),
      isSessionActive: () => true,
      verifyFounder: () async => founderState(user: 'other'),
      request: (_) async {
        called++;
        return {};
      },
      fetchMemories: () async => [],
      remember: (_, _) async => throw StateError('unexpected'),
    );
    expect((await bridge.handle(command('list')))['ok'], false);
    expect(called, 0);
  });

  test(
    'Assistant persona and cross-tenant conversations are rejected',
    () async {
      for (final persona in ['assistant', 'li']) {
        final bridge = LiWebBridge(
          session: session(),
          isSessionActive: () => true,
          verifyFounder: () async => founderState(),
          request: (_) async => {
            'binding': binding('li'),
            'conversations': [
              {
                'conversation_id': 'c1',
                'binding': persona == 'li'
                    ? {...binding('li'), 'tenant_id': 'other'}
                    : binding(persona),
              },
            ],
          },
          fetchMemories: () async => [],
          remember: (_, _) async => throw StateError('unexpected'),
        );
        expect((await bridge.handle(command('list')))['ok'], false);
      }
    },
  );

  test(
    'founder history can be reloaded through authenticated adapter',
    () async {
      final stored = {
        'conversation_id': 'c1',
        'version': 2,
        'binding': binding('li'),
        'messages': [
          {'role': 'user', 'text': 'saved'},
        ],
      };
      final bridge = LiWebBridge(
        session: session(),
        isSessionActive: () => true,
        verifyFounder: () async => founderState(),
        request: (input) async => input['operation'] == 'list'
            ? {
                'binding': binding('li'),
                'conversations': [
                  {'conversation_id': 'c1', 'binding': binding('li')},
                ],
              }
            : {'binding': binding('li'), 'conversation': stored},
        fetchMemories: () async => [],
        remember: (_, _) async => throw StateError('unexpected'),
      );
      expect((await bridge.handle(command('list')))['ok'], true);
      final fetched = await bridge.handle(
        command('get', {'conversation_id': 'c1'}),
      );
      expect(fetched['ok'], true);
      expect(
        ((fetched['data'] as Map)['conversation'] as Map)['messages'],
        stored['messages'],
      );
    },
  );

  test('session expiry rejects response after awaited adapter', () async {
    var active = true;
    final bridge = LiWebBridge(
      session: session(),
      isSessionActive: () => active,
      verifyFounder: () async => founderState(),
      request: (_) async {
        active = false;
        return {'binding': binding('li'), 'conversations': []};
      },
      fetchMemories: () async => [],
      remember: (_, _) async => throw StateError('unexpected'),
    );
    expect((await bridge.handle(command('list')))['ok'], false);
  });

  test('injected identity and unsupported operations never dispatch', () async {
    var count = 0;
    final bridge = LiWebBridge(
      session: session(),
      isSessionActive: () => true,
      verifyFounder: () async => founderState(),
      request: (_) async {
        count++;
        return {};
      },
      fetchMemories: () async => [],
      remember: (_, _) async => throw StateError('unexpected'),
    );
    expect(
      (await bridge.handle(command('list', {'tenant_id': 'other'})))['ok'],
      false,
    );
    expect((await bridge.handle(command('approve')))['ok'], false);
    expect(count, 0);
  });
}
