import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/account_lifecycle_client.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client_core.dart';

class _FakeTransport implements ControlPlaneTransport {
  _FakeTransport(this.responses);

  final Map<String, ControlPlaneResponse> responses;
  final List<({String method, Uri uri, Map<String, String> headers, String body})>
      requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    throw StateError('Account lifecycle client must not use GET');
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
  providerId: 'github',
  principalId: 'user-1',
  tenantId: 'tenant-1',
);

void main() {
  test('export invokes canonical route with canonical desktop session binding', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/api/account/export': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"status":"exported","data":{"user":{"user_id":"user-1"}}}',
      ),
    });
    final client = AccountLifecycleClient(
      baseUri: Uri.parse('http://localhost:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    final data = await client.exportMyData(_session);

    expect(data['user'], <String, dynamic>{'user_id': 'user-1'});
    final request = transport.requests.single;
    expect(request.method, 'POST');
    expect(request.uri.path, '/api/account/export');
    expect(request.headers, <String, String>{
      'Authorization': 'Bearer runtime-secret',
      'X-ILAIOS-Session': 'session-1',
    });
    expect(jsonDecode(request.body), <String, dynamic>{});
    expect(request.body, isNot(contains('user-1')));
    expect(request.body, isNot(contains('tenant-1')));
    expect(request.body, isNot(contains('github')));
  });

  test('export fails closed on auth and malformed response', () async {
    final denied = AccountLifecycleClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: _FakeTransport(<String, ControlPlaneResponse>{
        '/api/account/export': const ControlPlaneResponse(
          statusCode: 403,
          body: '{"error":"IDENTITY_DENIED"}',
        ),
      }),
    );
    await expectLater(
      denied.exportMyData(_session),
      throwsA(isA<ControlPlaneClientException>()),
    );

    final malformed = AccountLifecycleClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: _FakeTransport(<String, ControlPlaneResponse>{
        '/api/account/export': const ControlPlaneResponse(
          statusCode: 200,
          body: '{"status":"exported"}',
        ),
      }),
    );
    await expectLater(
      malformed.exportMyData(_session),
      throwsA(isA<ControlPlaneClientException>()),
    );
  });

  test('export rejects invalid loopback token and session authority', () async {
    expect(
      () => AccountLifecycleClient(
        baseUri: Uri.parse('https://ilaios.com'),
        token: 'runtime-secret',
        transport: _FakeTransport(const <String, ControlPlaneResponse>{}),
      ),
      throwsArgumentError,
    );
    expect(
      () => AccountLifecycleClient(
        baseUri: Uri.parse('http://127.0.0.1:4123'),
        token: 'runtime secret',
        transport: _FakeTransport(const <String, ControlPlaneResponse>{}),
      ),
      throwsArgumentError,
    );

    final client = AccountLifecycleClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: _FakeTransport(const <String, ControlPlaneResponse>{}),
    );
    const invalidSession = DesktopUserSession(
      sessionId: 'session 1',
      providerId: 'github',
      principalId: 'user-1',
      tenantId: 'tenant-1',
    );
    await expectLater(
      client.exportMyData(invalidSession),
      throwsA(isA<ControlPlaneClientException>()),
    );
  });
}
