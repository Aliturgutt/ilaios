import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'config.dart';

class DesktopRuntime {
  DesktopRuntime._({
    required this.config,
    required this.status,
    this._process,
  });

  final ControlPlaneConfig? config;
  final String status;
  final Process? _process;

  factory DesktopRuntime.unavailable(String status) => DesktopRuntime._(
        config: null,
        status: status,
      );

  static Future<DesktopRuntime> resolve() async {
    final configured = await ControlPlaneConfig.fromEnvironment();
    if (configured != null) {
      return DesktopRuntime._(
        config: configured,
        status: 'Using trusted externally configured control plane',
      );
    }
    if (!Platform.isWindows) {
      return DesktopRuntime.unavailable(
        'Bundled local control plane is available on Windows builds only',
      );
    }
    try {
      return await _startBundledWindowsRuntime();
    } on Object catch (error) {
      return DesktopRuntime.unavailable(
        'Bundled local control plane failed to start: $error',
      );
    }
  }

  static Future<DesktopRuntime> _startBundledWindowsRuntime() async {
    final executableDirectory = File(Platform.resolvedExecutable).parent;
    final sidecar = File('${executableDirectory.path}\\ilaios_control_plane.exe');
    if (!await sidecar.exists()) {
      return DesktopRuntime.unavailable(
        'Bundled ILAIOS control plane is not present in this build',
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
      mode: ProcessStartMode.normal,
    );
    unawaited(process.stdout.drain<void>());
    unawaited(process.stderr.drain<void>());

    try {
      final config = await _waitForReadiness(readyFile, token);
      return DesktopRuntime._(
        config: config,
        status: 'Bundled local control plane started',
        process: process,
      );
    } on Object {
      try {
        await process.stdin.close();
      } on Object {
        // Best-effort parent-pipe shutdown before forced termination.
      }
      if (!await _waitForExit(process, const Duration(seconds: 2))) {
        process.kill();
        await _waitForExit(process, const Duration(seconds: 2));
      }
      rethrow;
    }
  }

  static Future<ControlPlaneConfig> _waitForReadiness(
    File readyFile,
    String token,
  ) async {
    const attempts = 150;
    for (var attempt = 0; attempt < attempts; attempt += 1) {
      if (await readyFile.exists()) {
        try {
          final decoded = jsonDecode(await readyFile.readAsString());
          if (decoded is Map<String, dynamic>) {
            final host = decoded['host'];
            final port = decoded['port'];
            final identityHost = decoded['identity_host'];
            final identityPort = decoded['identity_port'];
            if (host is String &&
                port is int &&
                port > 0 &&
                port <= 65535 &&
                identityHost is String &&
                identityPort is int &&
                identityPort > 0 &&
                identityPort <= 65535) {
              return ControlPlaneConfig(
                baseUri: Uri(scheme: 'http', host: host, port: port),
                identityUri: Uri(
                  scheme: 'http',
                  host: identityHost,
                  port: identityPort,
                ),
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

  static Future<bool> _waitForExit(Process process, Duration timeout) async {
    try {
      await process.exitCode.timeout(timeout);
      return true;
    } on TimeoutException {
      return false;
    }
  }

  void dispose() {
    if (_process != null) {
      unawaited(_shutdownBundledRuntime());
    }
  }

  Future<void> _shutdownBundledRuntime() async {
    final process = _process;
    final runtimeConfig = config;
    if (process == null) return;

    final identityUri = runtimeConfig?.identityUri;
    if (identityUri != null && runtimeConfig != null) {
      final client = HttpClient();
      try {
        final request = await client
            .postUrl(identityUri.resolve('/v1/runtime/shutdown'))
            .timeout(const Duration(seconds: 1));
        request.headers.set(
          HttpHeaders.authorizationHeader,
          'Bearer ${runtimeConfig.token}',
        );
        request.headers.contentType = ContentType.json;
        final body = utf8.encode('{}');
        request.contentLength = body.length;
        request.add(body);
        final response = await request.close().timeout(const Duration(seconds: 1));
        await response.drain<void>().timeout(const Duration(seconds: 1));
        if (response.statusCode == HttpStatus.accepted &&
            await _waitForExit(process, const Duration(seconds: 3))) {
          return;
        }
      } on Object {
        // Parent-pipe EOF and forced termination remain bounded fallbacks.
      } finally {
        client.close(force: true);
      }
    }

    try {
      await process.stdin.close();
    } on Object {
      // The pipe may already be closed if the sidecar has started exiting.
    }
    if (await _waitForExit(process, const Duration(seconds: 3))) return;

    process.kill();
    await _waitForExit(process, const Duration(seconds: 2));
  }
}

class DesktopRuntimeException implements Exception {
  const DesktopRuntimeException(this.message);
  final String message;

  @override
  String toString() => 'DesktopRuntimeException: $message';
}
