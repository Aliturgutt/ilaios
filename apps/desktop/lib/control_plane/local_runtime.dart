import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'config.dart';

class DesktopRuntime {
  DesktopRuntime._({
    required this.config,
    required this.status,
    Process? process,
  }) : _process = process;

  final ControlPlaneConfig? config;
  final String status;
  final Process? _process;

  static Future<DesktopRuntime> resolve() async {
    final configured = await ControlPlaneConfig.fromEnvironment();
    if (configured != null) {
      return DesktopRuntime._(
        config: configured,
        status: 'Using trusted externally configured control plane',
      );
    }
    if (!Platform.isWindows) {
      return DesktopRuntime._(
        config: null,
        status: 'Bundled local control plane is available on Windows builds only',
      );
    }
    return _startBundledWindowsRuntime();
  }

  static Future<DesktopRuntime> _startBundledWindowsRuntime() async {
    final executableDirectory = File(Platform.resolvedExecutable).parent;
    final sidecar = File('${executableDirectory.path}\\ilaios_control_plane.exe');
    if (!await sidecar.exists()) {
      return DesktopRuntime._(
        config: null,
        status: 'Bundled ILAIOS control plane is not present in this build',
      );
    }

    final localAppData = Platform.environment['LOCALAPPDATA']?.trim();
    final fallback = Platform.environment['TEMP']?.trim();
    final base = localAppData?.isNotEmpty == true
        ? localAppData!
        : (fallback?.isNotEmpty == true ? fallback! : executableDirectory.path);
    final dataRoot = Directory('$base\\ILAIOS\\control-plane');
    await dataRoot.create(recursive: true);
    final readyFile = File('${dataRoot.path}\\control-plane-ready.json');
    if (await readyFile.exists()) {
      await readyFile.delete();
    }

    final token = _randomBearerToken();
    final environment = Map<String, String>.from(Platform.environment)
      ..['ILAIOS_CONTROL_PLANE_TOKEN'] = token;
    final process = await Process.start(
      sidecar.path,
      <String>[
        '--data-root',
        dataRoot.path,
        '--ready-file',
        readyFile.path,
      ],
      environment: environment,
      mode: ProcessStartMode.detachedWithStdio,
    );

    try {
      final config = await _waitForReadiness(readyFile, token);
      return DesktopRuntime._(
        config: config,
        status: 'Bundled local control plane started',
        process: process,
      );
    } on Object {
      process.kill();
      rethrow;
    }
  }

  static Future<ControlPlaneConfig> _waitForReadiness(
    File readyFile,
    String token,
  ) async {
    const attempts = 100;
    for (var attempt = 0; attempt < attempts; attempt += 1) {
      if (await readyFile.exists()) {
        try {
          final decoded = jsonDecode(await readyFile.readAsString());
          if (decoded is Map<String, dynamic>) {
            final host = decoded['host'];
            final port = decoded['port'];
            if (host is String && port is int && port > 0 && port <= 65535) {
              return ControlPlaneConfig(
                baseUri: Uri(scheme: 'http', host: host, port: port),
                token: token,
              );
            }
          }
        } on FormatException {
          // A partially written readiness file is retried until the deadline.
        } on FileSystemException {
          // Transient readiness-file access is retried until the deadline.
        }
      }
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }
    throw const DesktopRuntimeException(
      'Bundled local control plane did not become ready',
    );
  }

  static String _randomBearerToken() {
    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    return base64Url.encode(bytes).replaceAll('=', '');
  }

  void dispose() {
    _process?.kill();
  }
}

class DesktopRuntimeException implements Exception {
  const DesktopRuntimeException(this.message);
  final String message;

  @override
  String toString() => 'DesktopRuntimeException: $message';
}
