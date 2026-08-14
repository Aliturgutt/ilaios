import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

class _FakeTransport implements ControlPlaneTransport {
  _FakeTransport(this.responses);

  final Map<String, ControlPlaneResponse> responses;
  final List<({String method, Uri uri, Map<String, String> headers, String? body})>
      requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'GET', uri: uri, headers: Map.of(headers), body: null));
    return _response(uri.path);
  }

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'POST', uri: uri, headers: Map.of(headers), body: body));
    return _response(uri.path);
  }

  ControlPlaneResponse _response(String path) {
    final response = responses[path];
    if (response == null) throw StateError('No fake response for $path');
    return response;
  }
}

void main() {
  test('loads configured identity providers without exposing provider secrets', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/auth/providers': const ControlPlaneResponse(
        statusCode: 200,
        body:
            '{"providers":[{"provider_id":"google","display_name":"Google"},{"provider_id":"microsoft","display_name":"Microsoft"}]}',
      ),
    });
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );

    final providers = await client.fetchProviders();

    expect(providers, hasLength(2));
    expect(providers.first.providerId, 'google');
    expect(providers.last.displayName, 'Microsoft');
    expect(
      transport.requests.single.headers['Authorization'],
      'Bearer local-transport-token',
    );
  });

  test('starts HTTPS browser authorization and accepts only ILAIOS session metadata', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/auth/start': const ControlPlaneResponse(
        statusCode: 201,
        body:
            '{"provider_id":"google","state":"state-1","authorization_url":"https://accounts.example.test/authorize?state=state-1"}',
      ),
      '/v1/auth/status': const ControlPlaneResponse(
        statusCode: 200,
        body:
            '{"state":"state-1","status":"authenticated","provider_id":"google","session_id":"session-1","principal_id":"principal-1","tenant_id":"tenant-1","display_identity":"user@example.test"}',
      ),
    });
    final client = IdentityClient(
      baseUri: Uri.parse('http://localhost:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );

    final started = await client.start('google');
    final session = await client.poll(started.state);

    expect(started.authorizationUri.scheme, 'https');
    expect(session, isNotNull);
    expect(session!.sessionId, 'session-1');
    expect(session.tenantId, 'tenant-1');
    expect(session.displayIdentity, 'user@example.test');
    expect(transport.requests.first.body, jsonEncode(<String, Object?>{
      'provider_id': 'google',
    }));
  });

  test('authenticated prompt goes through session broker rather than direct client authority', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/desktop/intent': const ControlPlaneResponse(
        statusCode: 201,
        body:
            '{"goal_id":"goal-1","job_id":"job-1","state":"PENDING","principal_id":"principal-1","tenant_id":"tenant-1"}',
      ),
    });
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    const session = DesktopUserSession(
      sessionId: 'session-1',
      providerId: 'google',
      principalId: 'principal-1',
      tenantId: 'tenant-1',
    );

    final submission = await client.submitPrompt('Build a website', session);

    expect(submission.goalId, 'goal-1');
    expect(submission.jobId, 'job-1');
    final request = transport.requests.single;
    expect(request.uri.path, '/v1/desktop/intent');
    expect(request.headers['X-ILAIOS-Session'], 'session-1');
    expect(request.headers['Authorization'], 'Bearer local-transport-token');
  });

  test('identity client rejects non-loopback broker endpoints', () {
    expect(
      () => IdentityClient(
        baseUri: Uri.parse('https://example.com:43123'),
        transportToken: 'local-transport-token',
        transport: _FakeTransport(const <String, ControlPlaneResponse>{}),
      ),
      throwsArgumentError,
    );
  });
}
