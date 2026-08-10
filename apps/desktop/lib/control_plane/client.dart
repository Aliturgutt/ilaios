import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'projection.dart';

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
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  });
}

class IoControlPlaneTransport implements ControlPlaneTransport {
  const IoControlPlaneTransport({this.timeout = const Duration(seconds: 5)});

  final Duration timeout;

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    final client = HttpClient();
    try {
      final request = await client.getUrl(uri).timeout(timeout);
      headers.forEach(request.headers.set);
      final response = await request.close().timeout(timeout);
      final body = await utf8.decoder.bind(response).join().timeout(timeout);
      return ControlPlaneResponse(statusCode: response.statusCode, body: body);
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
  }) : _baseUri = _validatedBaseUri(baseUri),
       _token = _validatedToken(token),
       _transport = transport;

  final Uri _baseUri;
  final String _token;
  final ControlPlaneTransport _transport;

  Future<ControlPlaneProjection> fetchProjection() async {
    final readyResponse = await _transport.get(_baseUri.resolve('/health/ready'));
    final readyPayload = _decodeObject(readyResponse, 'readiness');
    if (readyResponse.statusCode != HttpStatus.ok || readyPayload['status'] != 'ready') {
      throw const ControlPlaneClientException('Authoritative control plane is not ready');
    }

    final eventResponse = await _transport.get(
      _baseUri.resolve('/v1/events'),
      headers: <String, String>{'Authorization': 'Bearer $_token'},
    );
    if (eventResponse.statusCode == HttpStatus.unauthorized ||
        eventResponse.statusCode == HttpStatus.forbidden) {
      throw const ControlPlaneClientException('Control plane authentication failed');
    }
    final eventPayload = _decodeObject(eventResponse, 'events');
    if (eventResponse.statusCode != HttpStatus.ok) {
      throw const ControlPlaneClientException('Control plane event query failed');
    }

    final rawEvents = eventPayload['events'];
    if (rawEvents is! List<Object?>) {
      throw const ControlPlaneClientException('Control plane returned malformed events');
    }

    var goalCount = 0;
    var jobCount = 0;
    String? lastEvent;
    for (final rawEvent in rawEvents) {
      if (rawEvent is! Map<String, dynamic>) {
        throw const ControlPlaneClientException('Control plane returned malformed event data');
      }
      final eventType = rawEvent['event_type'];
      if (eventType is! String) {
        throw const ControlPlaneClientException('Control plane event type is malformed');
      }
      if (eventType == 'goal.created') {
        goalCount += 1;
      } else if (eventType == 'job.created') {
        jobCount += 1;
      }
      lastEvent = eventType;
    }

    final schemaVersion = readyPayload['schema_version'];
    return ControlPlaneProjection(
      connected: true,
      status: 'Connected to authoritative control plane',
      goalCount: goalCount,
      jobCount: jobCount,
      lastEvent: lastEvent,
      schemaVersion: schemaVersion?.toString(),
    );
  }

  static Uri _validatedBaseUri(Uri uri) {
    final loopbackHost = uri.host == '127.0.0.1' || uri.host == '::1' || uri.host == 'localhost';
    if (uri.scheme != 'http' || !loopbackHost || !uri.hasPort) {
      throw ArgumentError.value(uri, 'baseUri', 'must be an explicit loopback HTTP endpoint');
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
    ControlPlaneResponse response,
    String label,
  ) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
    } on FormatException {
      // Converted to a stable client exception below.
    }
    throw ControlPlaneClientException('Control plane returned malformed $label JSON');
  }
}
