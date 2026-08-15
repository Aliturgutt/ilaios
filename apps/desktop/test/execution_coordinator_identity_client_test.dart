import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

class _ExecutionTransport implements ControlPlaneTransport {
  _ExecutionTransport(this.responses);

  final Map<String, ControlPlaneResponse> responses;
  final List<({String method, Uri uri, Map<String, String> headers, String? body})>
      requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'GET', uri: uri, headers: Map.of(headers), body: null));
    final response = responses[uri.path];
    if (response == null) throw StateError('No fake response for ${uri.path}');
    return response;
  }

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'POST', uri: uri, headers: Map.of(headers), body: body));
    final response = responses[uri.path];
    if (response == null) throw StateError('No fake response for ${uri.path}');
    return response;
  }
}

const _session = DesktopUserSession(
  sessionId: 'session-1',
  providerId: 'google',
  principalId: 'principal-1',
  tenantId: 'tenant-1',
);

void main() {
  test('authenticated intent carries a bounded idempotency key', () async {
    final transport = _ExecutionTransport(<String, ControlPlaneResponse>{
      '/v1/desktop/intent': const ControlPlaneResponse(
        statusCode: 201,
        body:
            '{"request_id":"exec-stable","goal_id":"goal-1","job_id":"job-1","state":"ADMITTED","execution_status":"ADMITTED"}',
      ),
    });
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'transport-token',
      transport: transport,
    );

    final submission = await client.submitPrompt(
      'Create a launch video',
      _session,
      idempotencyKey: 'intent-2026-08-16-1',
    );

    expect(submission.requestId, 'exec-stable');
    final request = transport.requests.single;
    expect(request.uri.path, '/v1/desktop/intent');
    expect(request.headers['X-ILAIOS-Session'], 'session-1');
    expect(
      jsonDecode(request.body!) as Map<String, dynamic>,
      <String, dynamic>{
        'objective': 'Create a launch video',
        'idempotency_key': 'intent-2026-08-16-1',
      },
    );
  });

  test('idempotency key validation fails closed before transport', () async {
    final transport = _ExecutionTransport(const <String, ControlPlaneResponse>{});
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'transport-token',
      transport: transport,
    );

    await expectLater(
      client.submitPrompt(
        'Create a launch video',
        _session,
        idempotencyKey: '   ',
      ),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.requests, isEmpty);
  });

  test('execution cancellation is session scoped and accepts only CANCELLED', () async {
    final transport = _ExecutionTransport(<String, ControlPlaneResponse>{
      '/v1/execution/cancel': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"request_id":"exec-1","execution_status":"CANCELLED"}',
      ),
    });
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'transport-token',
      transport: transport,
    );

    final status = await client.cancelExecution('exec-1', _session);

    expect(status, 'CANCELLED');
    final request = transport.requests.single;
    expect(request.uri.path, '/v1/execution/cancel');
    expect(request.headers['X-ILAIOS-Session'], 'session-1');
    expect(
      jsonDecode(request.body!) as Map<String, dynamic>,
      <String, dynamic>{'request_id': 'exec-1'},
    );
  });
}
