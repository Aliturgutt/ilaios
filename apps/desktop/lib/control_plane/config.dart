import 'dart:convert';
import 'dart:io';

bool isExplicitLoopbackHttpEndpoint(Uri uri) {
  final loopbackHost =
      uri.host == '127.0.0.1' || uri.host == '::1' || uri.host == 'localhost';
  return uri.scheme == 'http' && loopbackHost && uri.hasPort;
}

class ControlPlaneConfig {
  const ControlPlaneConfig({
    required this.baseUri,
    required this.token,
    this.identityUri,
    this.approverId,
  });

  final Uri baseUri;
  final Uri? identityUri;
  final String token;
  final String? approverId;

  static Future<ControlPlaneConfig?> fromEnvironment({
    Map<String, String>? environment,
  }) async {
    final env = environment ?? Platform.environment;
    final token = env['ILAIOS_CONTROL_PLANE_TOKEN']?.trim() ?? '';
    if (token.isEmpty) {
      return null;
    }
    final rawApproverId = env['ILAIOS_APPROVER_ID']?.trim() ?? '';
    final approverId = rawApproverId.isEmpty ? null : rawApproverId;
    final rawIdentityUrl = env['ILAIOS_IDENTITY_URL']?.trim() ?? '';
    final explicitIdentity =
        rawIdentityUrl.isEmpty ? null : Uri.parse(rawIdentityUrl);

    final explicitUrl = env['ILAIOS_CONTROL_PLANE_URL']?.trim() ?? '';
    if (explicitUrl.isNotEmpty) {
      return ControlPlaneConfig(
        baseUri: Uri.parse(explicitUrl),
        identityUri: explicitIdentity,
        token: token,
        approverId: approverId,
      );
    }

    final readyFilePath = env['ILAIOS_CONTROL_PLANE_READY_FILE']?.trim() ?? '';
    if (readyFilePath.isEmpty) {
      return null;
    }

    try {
      final decoded = jsonDecode(await File(readyFilePath).readAsString());
      if (decoded is! Map<String, dynamic>) {
        return null;
      }
      final host = decoded['host'];
      final port = decoded['port'];
      if (host is! String || port is! int) {
        return null;
      }
      Uri? identityUri = explicitIdentity;
      final identityHost = decoded['identity_host'];
      final identityPort = decoded['identity_port'];
      if (identityUri == null && identityHost is String && identityPort is int) {
        identityUri = Uri(scheme: 'http', host: identityHost, port: identityPort);
      }
      return ControlPlaneConfig(
        baseUri: Uri(scheme: 'http', host: host, port: port),
        identityUri: identityUri,
        token: token,
        approverId: approverId,
      );
    } on FileSystemException {
      return null;
    } on FormatException {
      return null;
    }
  }
}
