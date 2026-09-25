import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/assistant/assistant_web_bridge.dart';

void main() {
  test('only allowlisted operations reach the authenticated adapter', () async {
    final calls = <Map<String, Object?>>[];
    final bridge = AssistantWebBridge(
      userId: 'usr_user',
      tenantId: 'tnt_user',
      isSessionActive: () => true,
      request: (request) async {
        calls.add(request);
        return {
          'binding': {
            'user_id': 'usr_user',
            'tenant_id': 'tnt_user',
            'project_id': null,
            'workload_id': null,
            'persona': 'assistant',
          },
          'conversations': [],
        };
      },
    );
    final valid = await bridge.handle(
      jsonEncode({'id': '1', 'operation': 'list'}),
    );
    expect(valid['ok'], true);
    expect(calls, [
      {'operation': 'list'},
    ]);
    for (final operation in ['delete', 'approve', 'run', 'download', 'li']) {
      final result = await bridge.handle(
        jsonEncode({'id': '2', 'operation': operation}),
      );
      expect(result['ok'], false);
    }
    expect(calls.length, 1);
  });

  test('rejects injected identity and malformed sends', () async {
    var count = 0;
    final bridge = AssistantWebBridge(
      userId: 'usr_user',
      tenantId: 'tnt_user',
      isSessionActive: () => true,
      request: (request) async {
        count++;
        return {};
      },
    );
    for (final args in [
      {'user_id': 'other'},
      {
        'conversation_id': 'x',
        'version': 1,
        'text': 'hello',
        'message_id': 'm',
        'locale': 'tr',
        'tenant_id': 'other',
      },
      {
        'conversation_id': 'x',
        'version': 1,
        'text': '',
        'message_id': 'm',
        'locale': 'tr',
      },
    ]) {
      expect(
        (await bridge.handle(
          jsonEncode({'id': 'a', 'operation': 'send', 'args': args}),
        ))['ok'],
        false,
      );
    }
    expect(count, 0);
  });
  test(
    'service failure is fail-closed without leaking backend details',
    () async {
      final bridge = AssistantWebBridge(
        userId: 'usr_user',
        tenantId: 'tnt_user',
        isSessionActive: () => true,
        request: (_) async => throw StateError('private token'),
      );
      final result = await bridge.handle(
        jsonEncode({'id': 'safe', 'operation': 'list'}),
      );
      expect(result['ok'], false);
      expect(result['error'].toString(), isNot(contains('private token')));
    },
  );

  test(
    'unknown arguments and malformed payloads never reach backend',
    () async {
      var calls = 0;
      final bridge = AssistantWebBridge(
        userId: 'usr_user',
        tenantId: 'tnt_user',
        isSessionActive: () => true,
        request: (_) async {
          calls++;
          return {};
        },
      );
      for (final raw in [
        'not json',
        '[]',
        jsonEncode({
          'id': 'x',
          'operation': 'list',
          'args': {'tenant_id': 'forged'},
        }),
        jsonEncode({'id': 'x', 'operation': 'get', 'args': {}}),
      ]) {
        expect((await bridge.handle(raw))['ok'], false);
      }
      expect(calls, 0);
    },
  );
  test('rejects requests after session invalidation', () async {
    var active = true;
    var calls = 0;
    final bridge = AssistantWebBridge(
      userId: 'usr_user',
      tenantId: 'tnt_user',
      isSessionActive: () => active,
      request: (_) async {
        calls++;
        return {
          'binding': {
            'user_id': 'usr_user',
            'tenant_id': 'tnt_user',
            'project_id': null,
            'workload_id': null,
            'persona': 'assistant',
          },
          'conversations': [],
        };
      },
    );
    active = false;
    final result = await bridge.handle(
      jsonEncode({'id': 'expired', 'operation': 'list'}),
    );
    expect(result['ok'], false);
    expect(calls, 0);
  });

  test('discards in-flight response when session changes', () async {
    var active = true;
    final response = Completer<Map<String, dynamic>>();
    final bridge = AssistantWebBridge(
      userId: 'usr_user',
      tenantId: 'tnt_user',
      isSessionActive: () => active,
      request: (_) => response.future,
    );
    final pending = bridge.handle(
      jsonEncode({'id': 'old', 'operation': 'list'}),
    );
    await Future<void>.delayed(Duration.zero);
    active = false;
    response.complete({
      'conversations': [
        {'conversation_id': 'private'},
      ],
    });
    final result = await pending;
    expect(result['ok'], false);
    expect(result.containsKey('data'), false);
  });
}
