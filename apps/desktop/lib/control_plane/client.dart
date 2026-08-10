import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'evidence_record.dart';
import 'operational_snapshot.dart';
import 'projection.dart';

enum GovernanceDecision {
  approved('approved'),
  denied('denied');

  const GovernanceDecision(this.wireValue);
  final String wireValue;
}

class ControlPlaneClientException implements Exception {
  const ControlPlaneClientException(this.message);
  final String message;
  @override
  String toString() => 'ControlPlaneClientException: $message';
}

class ControlPlaneResponse {
  const ControlPlaneResponse({required this.statusCode, required this.body});
  final int statusCode;
  final String body;
}

abstract interface class ControlPlaneTransport {
  Future<ControlPlaneResponse> get(Uri uri,
      {Map<String, String> headers = const <String, String>{}});
  Future<ControlPlaneResponse> post(Uri uri,
      {required String body,
      Map<String, String> headers = const <String, String>{}});
}

class IoControlPlaneTransport implements ControlPlaneTransport {
  const IoControlPlaneTransport({this.timeout = const Duration(seconds: 5)});
  final Duration timeout;

  @override
  Future<ControlPlaneResponse> get(Uri uri,
          {Map<String, String> headers = const <String, String>{}}) =>
      _request('GET', uri, headers: headers);

  @override
  Future<ControlPlaneResponse> post(Uri uri,
          {required String body,
          Map<String, String> headers = const <String, String>{}}) =>
      _request('POST', uri, body: body, headers: headers);

  Future<ControlPlaneResponse> _request(String method, Uri uri,
      {String? body,
      Map<String, String> headers = const <String, String>{}}) async {
    final client = HttpClient();
    try {
      final request = await client.openUrl(method, uri).timeout(timeout);
      headers.forEach(request.headers.set);
      if (body != null) {
        request.headers.contentType = ContentType.json;
        request.write(body);
      }
      final response = await request.close().timeout(timeout);
      final responseBody =
          await utf8.decoder.bind(response).join().timeout(timeout);
      return ControlPlaneResponse(
          statusCode: response.statusCode, body: responseBody);
    } on TimeoutException {
      throw const ControlPlaneClientException('Control plane request timed out');
    } on SocketException {
      throw const ControlPlaneClientException('Control plane is unreachable');
    } on HttpException {
      throw const ControlPlaneClientException('Control plane transport failed');
    } finally {
      client.close(force: true);
    }
  }
}

class ControlPlaneClient {
  ControlPlaneClient({
    required Uri baseUri,
    required String token,
    ControlPlaneTransport transport = const IoControlPlaneTransport(),
  })  : _baseUri = _validatedBaseUri(baseUri),
        _token = _validatedToken(token),
        _transport = transport;

  final Uri _baseUri;
  final String _token;
  final ControlPlaneTransport _transport;

  Future<ControlPlaneProjection> fetchProjection() async {
    final readyResponse = await _transport.get(_baseUri.resolve('/health/ready'));
    final readyPayload = _decodeObject(readyResponse, 'readiness');
    if (readyResponse.statusCode != HttpStatus.ok ||
        readyPayload['status'] != 'ready') {
      throw const ControlPlaneClientException(
          'Authoritative control plane is not ready');
    }
    final eventPayload = await _getAuthenticatedObject('/v1/events', 'events');
    final rawEvents = eventPayload['events'];
    if (rawEvents is! List<Object?>) {
      throw const ControlPlaneClientException(
          'Control plane returned malformed events');
    }
    var goalCount = 0;
    var jobCount = 0;
    String? lastEvent;
    for (final rawEvent in rawEvents) {
      if (rawEvent is! Map<String, dynamic> ||
          rawEvent['event_type'] is! String) {
        throw const ControlPlaneClientException(
            'Control plane returned malformed event data');
      }
      final eventType = rawEvent['event_type'] as String;
      if (eventType == 'goal.created') goalCount += 1;
      if (eventType == 'job.created') jobCount += 1;
      lastEvent = eventType;
    }
    return ControlPlaneProjection(
      connected: true,
      status: 'Connected to authoritative control plane',
      goalCount: goalCount,
      jobCount: jobCount,
      lastEvent: lastEvent,
      schemaVersion: readyPayload['schema_version']?.toString(),
    );
  }

  Future<OperationalSnapshot> fetchOperationalSnapshot() async {
    final runtimePayload =
        await _getAuthenticatedObject('/v1/runtime/routes', 'runtime routes');
    final schedulerPayload =
        await _getAuthenticatedObject('/v1/scheduler/state', 'scheduler state');
    final grantsPayload =
        await _getAuthenticatedObject('/v1/grants/state', 'grant state');
    final governancePayload = await _getAuthenticatedObject(
        '/v1/governance/state', 'governance state');
    final evidencePayload = await _getAuthenticatedObject(
        '/v1/evidence/verify', 'evidence verification');
    final livePayload =
        await _getAuthenticatedObject('/v1/live/events', 'live events');

    return OperationalSnapshot(
      runtimeRoutes: _objectList(runtimePayload['routes'], 'runtime routes'),
      schedulerState: Map<String, Object?>.from(schedulerPayload),
      grantsState: Map<String, Object?>.from(grantsPayload),
      governanceState: Map<String, Object?>.from(governancePayload),
      evidenceRecords: _evidenceList(evidencePayload['records']),
      liveEvents: _objectList(livePayload['events'], 'live events'),
    );
  }

  Future<void> decideGovernanceRequest({
    required String requestId,
    required String approver,
    required GovernanceDecision decision,
  }) async {
    final normalizedRequestId = requestId.trim();
    final normalizedApprover = approver.trim();
    if (normalizedRequestId.isEmpty || normalizedApprover.isEmpty) {
      throw const ControlPlaneClientException(
          'Governance decision requires request and approver identifiers');
    }
    final response = await _transport.post(
      _baseUri.resolve('/v1/governance/commands'),
      body: jsonEncode(<String, Object?>{
        'operation': 'decide',
        'request_id': normalizedRequestId,
        'approver': normalizedApprover,
        'decision': decision.wireValue,
      }),
      headers: <String, String>{'Authorization': 'Bearer $_token'},
    );
    if (response.statusCode == HttpStatus.unauthorized) {
      throw const ControlPlaneClientException(
          'Control plane authentication failed');
    }
    if (response.statusCode != HttpStatus.ok) {
      throw const ControlPlaneClientException(
          'Governance decision rejected by authoritative control plane');
    }
    if (_decodeObject(response, 'governance decision')['decided'] != true) {
      throw const ControlPlaneClientException(
          'Control plane returned malformed governance decision');
    }
  }

  Future<Map<String, dynamic>> _getAuthenticatedObject(
      String path, String label) async {
    final response = await _transport.get(_baseUri.resolve(path),
        headers: <String, String>{'Authorization': 'Bearer $_token'});
    if (response.statusCode == HttpStatus.unauthorized) {
      throw const ControlPlaneClientException(
          'Control plane authentication failed');
    }
    if (response.statusCode != HttpStatus.ok) {
      throw ControlPlaneClientException('Control plane $label query failed');
    }
    return _decodeObject(response, label);
  }

  static List<EvidenceRecord> _evidenceList(Object? raw) {
    if (raw is! List<Object?>) {
      throw const ControlPlaneClientException(
          'Control plane returned malformed evidence records');
    }
    try {
      return List<EvidenceRecord>.unmodifiable(raw.map((item) {
        if (item is! Map<String, dynamic>) {
          throw const FormatException('Malformed verified evidence record');
        }
        return EvidenceRecord.fromJson(item);
      }));
    } on FormatException {
      throw const ControlPlaneClientException(
          'Control plane returned malformed evidence records');
    }
  }

  static List<Map<String, Object?>> _objectList(Object? raw, String label) {
    if (raw is! List<Object?>) {
      throw ControlPlaneClientException('Control plane returned malformed $label');
    }
    final output = <Map<String, Object?>>[];
    for (final item in raw) {
      if (item is! Map<String, dynamic>) {
        throw ControlPlaneClientException(
            'Control plane returned malformed $label');
      }
      output.add(Map<String, Object?>.from(item));
    }
    return List<Map<String, Object?>>.unmodifiable(output);
  }

  static Uri _validatedBaseUri(Uri uri) {
    final loopbackHost =
        uri.host == '127.0.0.1' || uri.host == '::1' || uri.host == 'localhost';
    if (uri.scheme != 'http' || !loopbackHost || !uri.hasPort) {
      throw ArgumentError.value(uri, 'baseUri',
          'must be an explicit loopback HTTP endpoint');
    }
    return uri;
  }

  static String _validatedToken(String token) {
    if (token.trim().isEmpty) {
      throw ArgumentError.value(token, 'token', 'must not be empty');
    }
    return token;
  }

  static Map<String, dynamic> _decodeObject(
      ControlPlaneResponse response, String label) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) return decoded;
    } on FormatException {
      // Stabilized below.
    }
    throw ControlPlaneClientException(
        'Control plane returned malformed $label JSON');
  }
}
