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
    return _response(uri);
  }

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'POST', uri: uri, headers: Map.of(headers), body: body));
    return _response(uri);
  }

  ControlPlaneResponse _response(Uri uri) {
    final response = responses[uri.path];
    if (response == null) throw StateError('No fake response for ${uri.path}');
    return response;
  }
}

Map<String, ControlPlaneResponse> _operationalResponses({
  String evidenceBody =
      '{"records":[{"sequence":1,"execution_id":"exec-1","artifact_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","action":"render","previous_hash":"","record_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}]}',
}) {
  return <String, ControlPlaneResponse>{
    '/v1/runtime/routes': const ControlPlaneResponse(
      statusCode: 200,
      body: '{"routes":[{"sequence":1,"provider_id":"local","capability":"video"}]}',
    ),
    '/v1/scheduler/state': const ControlPlaneResponse(
      statusCode: 200,
      body: '{"leases":[],"effects":[]}',
    ),
    '/v1/grants/state': const ControlPlaneResponse(
      statusCode: 200,
      body: '{"grants":[],"revoked":[],"stopped":[]}',
    ),
    '/v1/governance/state': const ControlPlaneResponse(
      statusCode: 200,
      body: '{"work":[],"secret_references":[],"ledger":{}}',
    ),
    '/v1/evidence/verify': ControlPlaneResponse(statusCode: 200, body: evidenceBody),
    '/v1/live/events': const ControlPlaneResponse(
      statusCode: 200,
      body: '{"events":[{"sequence":1,"event_type":"job.updated"}]}',
    ),
  };
}

void main() {
  test('projects authoritative readiness and event state', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/health/ready': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"status":"ready","schema_version":1}',
      ),
      '/v1/events': const ControlPlaneResponse(
        statusCode: 200,
        body:
            '{"events":[{"event_type":"goal.created"},{"event_type":"goal.created"},{"event_type":"job.created"}]}',
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    final projection = await client.fetchProjection();

    expect(projection.connected, isTrue);
    expect(projection.goalCount, 2);
    expect(projection.jobCount, 1);
    expect(projection.lastEvent, 'job.created');
    expect(projection.schemaVersion, '1');
    expect(transport.requests.first.headers, isEmpty);
    expect(transport.requests.last.headers['Authorization'], 'Bearer runtime-secret');
  });

  test('loads operational APIs and typed verified evidence metadata', () async {
    final transport = _FakeTransport(_operationalResponses());
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    final snapshot = await client.fetchOperationalSnapshot();

    expect(snapshot.runtimeRouteCount, 1);
    expect(snapshot.runtimeRoutes.single['provider_id'], 'local');
    expect(snapshot.evidenceCount, 1);
    final record = snapshot.evidenceRecords.single;
    expect(record.sequence, 1);
    expect(record.executionId, 'exec-1');
    expect(record.action, 'render');
    expect(record.artifactDigest, hasLength(64));
    expect(record.recordHash, hasLength(64));
    expect(snapshot.liveEventCount, 1);
    expect(transport.requests, hasLength(6));
    for (final request in transport.requests) {
      expect(request.headers['Authorization'], 'Bearer runtime-secret');
    }
  });

  test('malformed evidence metadata fails closed', () async {
    final transport = _FakeTransport(_operationalResponses(
      evidenceBody: '{"records":[{"sequence":1,"content_base64":"forbidden"}]}',
    ));
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    await expectLater(
      client.fetchOperationalSnapshot(),
      throwsA(isA<ControlPlaneClientException>()),
    );
  });

  test('sends only backend-defined governance decision command', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/governance/commands': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"decided":true}',
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    await client.decideGovernanceRequest(
      requestId: 'request-1',
      approver: 'human-approver',
      decision: GovernanceDecision.approved,
    );

    final request = transport.requests.single;
    expect(request.method, 'POST');
    expect(request.uri.path, '/v1/governance/commands');
    final body = jsonDecode(request.body!) as Map<String, dynamic>;
    expect(body, <String, dynamic>{
      'operation': 'decide',
      'request_id': 'request-1',
      'approver': 'human-approver',
      'decision': 'approved',
    });
  });

  test('governance rejection remains fail closed', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/governance/commands': const ControlPlaneResponse(
        statusCode: 403,
        body: '{"error":"independent human approver is required"}',
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    await expectLater(
      client.decideGovernanceRequest(
        requestId: 'request-1',
        approver: 'requester-1',
        decision: GovernanceDecision.denied,
      ),
      throwsA(isA<ControlPlaneClientException>()),
    );
  });

  test('authentication rejection remains fail closed', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/health/ready': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"status":"ready","schema_version":1}',
      ),
      '/v1/events': const ControlPlaneResponse(
        statusCode: 401,
        body: '{"error":"invalid token"}',
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://localhost:4123'),
      token: 'wrong-secret',
      transport: transport,
    );

    await expectLater(client.fetchProjection(), throwsA(isA<ControlPlaneClientException>()));
  });

  test('rejects non-loopback control-plane endpoints', () {
    expect(
      () => ControlPlaneClient(
        baseUri: Uri.parse('http://example.com:4123'),
        token: 'runtime-secret',
        transport: _FakeTransport(const <String, ControlPlaneResponse>{}),
      ),
      throwsArgumentError,
    );
  });
}
