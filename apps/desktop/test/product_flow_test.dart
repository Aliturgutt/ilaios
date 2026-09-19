import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';

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
  test('one prompt creates goal then durable job through authenticated API', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/goals': const ControlPlaneResponse(
        statusCode: 201,
        body: '{"goal_id":"goal-00000001","objective":"Build a site"}',
      ),
      '/v1/jobs': const ControlPlaneResponse(
        statusCode: 201,
        body: '{"job_id":"job-00000001","goal_id":"goal-00000001","state":"PENDING"}',
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    final submission = await client.submitPrompt('  Build a site  ');

    expect(submission.goalId, 'goal-00000001');
    expect(submission.jobId, 'job-00000001');
    expect(submission.state, 'PENDING');
    expect(transport.requests, hasLength(2));
    expect(transport.requests.first.method, 'POST');
    expect(transport.requests.first.uri.path, '/v1/goals');
    expect(
      jsonDecode(transport.requests.first.body!) as Map<String, dynamic>,
      <String, dynamic>{'objective': 'Build a site'},
    );
    expect(transport.requests.last.uri.path, '/v1/jobs');
    for (final request in transport.requests) {
      expect(request.headers['Authorization'], 'Bearer runtime-secret');
    }
  });

  test('verified artifact retrieval accepts only server-verified payload shape', () async {
    const digest =
        '9f64a747e1b97f131fabb6b447296c9b6f0201e79fb3c5356e6c77e89b6a806a';
    final encoded = base64Encode(<int>[1, 2, 3, 4]);
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/evidence/artifacts/$digest': ControlPlaneResponse(
        statusCode: 200,
        body: jsonEncode(<String, Object?>{
          'digest': digest,
          'size': 4,
          'content_base64': encoded,
        }),
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://localhost:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    final artifact = await client.fetchVerifiedArtifact(digest);

    expect(artifact.digest, digest);
    expect(artifact.size, 4);
    expect(artifact.bytes, <int>[1, 2, 3, 4]);
  });

  test('artifact retrieval fails closed on inconsistent size', () async {
    final digest = List<String>.filled(64, 'b').join();
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/evidence/artifacts/$digest': ControlPlaneResponse(
        statusCode: 200,
        body: jsonEncode(<String, Object?>{
          'digest': digest,
          'size': 99,
          'content_base64': base64Encode(<int>[1, 2, 3]),
        }),
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    await expectLater(
      client.fetchVerifiedArtifact(digest),
      throwsA(isA<ControlPlaneClientException>()),
    );
  });
}
