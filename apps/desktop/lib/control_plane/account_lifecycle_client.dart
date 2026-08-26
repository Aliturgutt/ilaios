import 'dart:convert';
import 'dart:io';

import 'client.dart';

class AccountLifecycleClient {
  AccountLifecycleClient({
    required Uri baseUri,
    required String token,
    required ControlPlaneTransport transport,
  })  : _baseUri = _validateBaseUri(baseUri),
        _token = _validateToken(token),
        _transport = transport;

  final Uri _baseUri;
  final String _token;
  final ControlPlaneTransport _transport;

  Future<void> logoutCurrentSession() async {
    final payload = await _post('/api/account/sessions/logout', 'account logout');
    if (payload['status'] != 'logged_out') {
      throw const ControlPlaneClientException(
        'Control plane returned malformed account logout result',
      );
    }
  }

  Future<Map<String, Object?>> exportMyData() async {
    final payload = await _post('/api/account/export', 'account export');
    if (payload['status'] != 'exported' || payload['data'] is! Map<String, dynamic>) {
      throw const ControlPlaneClientException(
        'Control plane returned malformed account export result',
      );
    }
    return Map<String, Object?>.unmodifiable(
      Map<String, Object?>.from(payload['data'] as Map<String, dynamic>),
    );
  }

  Future<Map<String, dynamic>> _post(String path, String label) async {
    final response = await _transport.post(
      _baseUri.resolve(path),
      body: '{}',
      headers: <String, String>{'Authorization': 'Bearer $_token'},
    );
    if (response.statusCode == HttpStatus.unauthorized ||
        response.statusCode == HttpStatus.forbidden) {
      throw const ControlPlaneClientException(
        'Control plane authentication failed',
      );
    }
    if (response.statusCode != HttpStatus.ok) {
      throw ControlPlaneClientException('Control plane $label failed');
    }
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('response is not an object');
      }
      return decoded;
    } on FormatException {
      throw ControlPlaneClientException(
        'Control plane returned malformed $label response',
      );
    }
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
    if (normalized.isEmpty || normalized != token) {
      throw ArgumentError.value(token, 'token', 'A canonical bearer token is required');
    }
    return normalized;
  }
}
