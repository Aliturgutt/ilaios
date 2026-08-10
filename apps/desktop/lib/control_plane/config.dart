import 'dart:convert';
import 'dart:io';

class ControlPlaneConfig {
  const ControlPlaneConfig({
    required this.baseUri,
    required this.token,
    this.approverId,
  });

  final Uri baseUri;
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

    final explicitUrl = env['ILAIOS_CONTROL_PLANE_URL']?.trim() ?? '';
    if (explicitUrl.isNotEmpty) {
      return ControlPlaneConfig(
        baseUri: Uri.parse(explicitUrl),
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
      return ControlPlaneConfig(
        baseUri: Uri(scheme: 'http', host: host, port: port),
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
