import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

class _Transport implements ControlPlaneTransport {
  _Transport(this.payload);
  final Map<String, dynamic> payload;
  Map<String, String>? headers;
  Uri? uri;
  @override
  Future<ControlPlaneResponse> get(Uri uri, {Map<String, String> headers = const {}}) async =>
      throw StateError('unexpected GET');
  @override
  Future<ControlPlaneResponse> post(Uri uri, {required String body, Map<String, String> headers = const {}}) async {
    this.headers = headers;
    this.uri = uri;
    return ControlPlaneResponse(statusCode: 200, body: jsonEncode(payload));
  }
}

void main() {
  const session = DesktopUserSession(sessionId: 'session', providerId: 'google',
      principalId: 'usr_user', tenantId: 'tnt_user');
  Map<String, dynamic> binding() => {'user_id': 'usr_user', 'tenant_id': 'tnt_user',
    'project_id': null, 'workload_id': null, 'persona': 'assistant'};
  test('Assistant reuses authenticated transport headers', () async {
    final transport = _Transport({'binding': binding(), 'conversations': []});
    final client = IdentityClient(baseUri: Uri.parse('http://127.0.0.1:1234'),
        transportToken: 'transport', transport: transport);
    await client.assistantRequest(session, {'operation': 'list'});
    expect(transport.headers?['Authorization'], 'Bearer transport');
    expect(transport.headers?['X-ILAIOS-Session'], 'session');
    expect(transport.uri?.path, '/v1/assistant');
  });
  for (final field in ['user_id', 'tenant_id', 'project_id', 'workload_id', 'persona']) {
    test('wrong $field binding is rejected before UI exposure', () async {
      final wrong = binding()..[field] = 'wrong';
      final transport = _Transport({'binding': wrong, 'conversations': []});
      final client = IdentityClient(baseUri: Uri.parse('http://127.0.0.1:1234'),
          transportToken: 'transport', transport: transport);
      await expectLater(client.assistantRequest(session, {'operation': 'list'}),
          throwsA(isA<IdentityClientException>()));
    });
  }
  test('conversation cannot disagree with verified outer binding', () async {
    final transport = _Transport({'binding': binding(), 'conversation': {
      'binding': binding()..['user_id'] = 'other', 'messages': [],
    }});
    final client = IdentityClient(baseUri: Uri.parse('http://127.0.0.1:1234'),
        transportToken: 'transport', transport: transport);
    await expectLater(client.assistantRequest(session, {'operation': 'get', 'conversation_id': 'id'}),
        throwsA(isA<IdentityClientException>()));
  });
}
