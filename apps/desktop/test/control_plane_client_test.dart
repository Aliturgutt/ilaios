import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';

class _FakeTransport implements ControlPlaneTransport {
  _FakeTransport(this.responses);

  final Map<String, ControlPlaneResponse> responses;
  final List<({Uri uri, Map<String, String> headers})> requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((uri: uri, headers: Map<String, String>.from(headers)));
    final response = responses[uri.path];
    if (response == null) {
      throw StateError('No fake response for ${uri.path}');
    }
    return response;
  }
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
            '{"events":['
            '{"event_type":"goal.created"},'
            '{"event_type":"goal.created"},'
            '{"event_type":"job.created"}'
            ']}',
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
    expect(transport.requests, hasLength(2));
    expect(transport.requests.first.headers, isEmpty);
    expect(
      transport.requests.last.headers['Authorization'],
      'Bearer runtime-secret',
    );
  });

  test('loads verified operational APIs through authenticated queries', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/runtime/routes': const ControlPlaneResponse(
        statusCode: 200,
        body:
            '{"routes":[{"sequence":1,"provider_id":"local","capability":"video"}]}',
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
        body: '{"pending":0}',
      ),
      '/v1/evidence/verify': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"records":[{"digest":"abc"}]}',
      ),
      '/v1/live/events': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"events":[{"sequence":1,"event_type":"job.updated"}]}',
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    final snapshot = await client.fetchOperationalSnapshot();

    expect(snapshot.runtimeRouteCount, 1);
    expect(snapshot.runtimeRoutes.single['provider_id'], 'local');
    expect(snapshot.schedulerState['leases'], isEmpty);
    expect(snapshot.grantsState['grants'], isEmpty);
    expect(snapshot.governanceState['pending'], 0);
    expect(snapshot.evidenceCount, 1);
    expect(snapshot.liveEventCount, 1);
    expect(transport.requests, hasLength(6));
    for (final request in transport.requests) {
      expect(request.headers['Authorization'], 'Bearer runtime-secret');
    }
  });

  test('fails closed on authentication rejection', () async {
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

    await expectLater(
      client.fetchProjection(),
      throwsA(
        isA<ControlPlaneClientException>().having(
          (error) => error.message,
          'message',
          'Control plane authentication failed',
        ),
      ),
    );
  });

  test('operational APIs reject malformed authoritative envelopes', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/v1/runtime/routes': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"routes":{"unexpected":true}}',
      ),
      '/v1/scheduler/state': const ControlPlaneResponse(
        statusCode: 200,
        body: '{}',
      ),
      '/v1/grants/state': const ControlPlaneResponse(
        statusCode: 200,
        body: '{}',
      ),
      '/v1/governance/state': const ControlPlaneResponse(
        statusCode: 200,
        body: '{}',
      ),
      '/v1/evidence/verify': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"records":[]}',
      ),
      '/v1/live/events': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"events":[]}',
      ),
    });
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

  test('rejects malformed authoritative event data', () async {
    final transport = _FakeTransport(<String, ControlPlaneResponse>{
      '/health/ready': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"status":"ready","schema_version":1}',
      ),
      '/v1/events': const ControlPlaneResponse(
        statusCode: 200,
        body: '{"events":[{"unexpected":true}]}',
      ),
    });
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    await expectLater(
      client.fetchProjection(),
      throwsA(isA<ControlPlaneClientException>()),
    );
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
