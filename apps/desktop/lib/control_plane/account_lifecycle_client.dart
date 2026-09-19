import 'dart:convert';
import 'dart:io';

import '../identity/identity_client_core.dart';
import 'client.dart';

class AccountLifecycleClient {
  factory AccountLifecycleClient({
    required Uri baseUri,
    required String token,
    required ControlPlaneTransport transport,
  }) {
    return AccountLifecycleClient._(
      baseUri: _validateBaseUri(baseUri),
      token: _validateToken(token),
      transport: transport,
    );
  }

  AccountLifecycleClient._({
    required this._baseUri,
    required this._token,
    required this._transport,
  });

  final Uri _baseUri;
  final String _token;
  final ControlPlaneTransport _transport;

  Future<Map<String, Object?>> exportMyData(DesktopUserSession session) async {
    final sessionId = _validateSessionId(session.sessionId);
    final response = await _transport.post(
      _baseUri.resolve('/api/account/export'),
      body: '{}',
      headers: <String, String>{
        'Authorization': 'Bearer $_token',
        'X-ILAIOS-Session': sessionId,
      },
    );
    if (response.statusCode == HttpStatus.unauthorized ||
        response.statusCode == HttpStatus.forbidden) {
      throw const ControlPlaneClientException(
        'Desktop lifecycle session is invalid or expired',
      );
    }
    if (response.statusCode != HttpStatus.ok) {
      throw const ControlPlaneClientException('Control plane account export failed');
    }

    final Map<String, dynamic> payload;
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('response is not an object');
      }
      payload = decoded;
    } on FormatException {
      throw const ControlPlaneClientException(
        'Control plane returned malformed account export response',
      );
    }
    if (payload['status'] != 'exported' || payload['data'] is! Map<String, dynamic>) {
      throw const ControlPlaneClientException(
        'Control plane returned malformed account export result',
      );
    }
    return Map<String, Object?>.unmodifiable(
      Map<String, Object?>.from(payload['data'] as Map<String, dynamic>),
    );
  }

  static Uri _validateBaseUri(Uri uri) {
    final loopbackHost =
        uri.host == '127.0.0.1' || uri.host == '::1' || uri.host == 'localhost';
    if (uri.scheme != 'http' || !loopbackHost || !uri.hasPort) {
      throw ArgumentError.value(
        uri,
        'baseUri',
        'Account lifecycle client requires an explicit loopback HTTP endpoint',
      );
    }
    return uri;
  }

  static String _validateToken(String token) {
    final normalized = token.trim();
    if (normalized.isEmpty || normalized != token || token.contains(RegExp(r'\s'))) {
      throw ArgumentError.value(token, 'token', 'A canonical bearer token is required');
    }
    return normalized;
  }

  static String _validateSessionId(String sessionId) {
    final normalized = sessionId.trim();
    if (normalized.isEmpty ||
        normalized != sessionId ||
        sessionId.contains(RegExp(r'\s'))) {
      throw const ControlPlaneClientException('Desktop lifecycle session is invalid');
    }
    return normalized;
  }
}
