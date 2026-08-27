// Final current-master Desktop recertification trigger; no runtime behavior change.
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

    // Bundled Desktop instances must never share readiness state. A fixed
    // ready-file path lets a concurrently starting or exiting sidecar publish
    // ports that belong to a different bearer token. That cross-process race
    // presents exactly like a transport-authentication failure. Keep the data
    // root durable, but make the hand-off file private to this Desktop process.
    final readyFile = File(
      '${dataRoot.path}\\control-plane-ready-$pid-'
      '${DateTime.now().microsecondsSinceEpoch}.json',
    );

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
      // The bundled runtime is owned by the Desktop application, not by the
      // terminal or shell that happened to launch the GUI. Keep stdio so the
      // existing parent-pipe watchdog can still observe an intentional Desktop
      // exit/crash, while detaching the process group from an external console
      // lifetime. DesktopRuntime.dispose() remains the authoritative graceful
      // shutdown path through /v1/runtime/shutdown.
      mode: ProcessStartMode.detachedWithStdio,
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
    } finally {
      try {
        if (await readyFile.exists()) {
          await readyFile.delete();
        }
      } on FileSystemException {
        // The hand-off file is non-authoritative after readiness succeeds.
      }
    }
  }

  static Future<ControlPlaneConfig> _waitForReadiness(
    File readyFile,
    String token,
  ) async {
    // PyInstaller one-file extraction is subject to bounded Windows disk and
    // antivirus variance. Keep startup fail-closed, but align the product with
    // the packaged Windows diagnostic's 60-second cold-start evidence window
    // so a healthy child is not rejected earlier than the artifact we certify.
    const attempts = 600;
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
              final config = ControlPlaneConfig(
                baseUri: Uri(scheme: 'http', host: host, port: port),
                identityUri: Uri(
                  scheme: 'http',
                  host: identityHost,
                  port: identityPort,
                ),
                token: token,
              );

              // The ready file is an untrusted process hand-off boundary. Do
              // not send the per-process bearer anywhere until both published
              // endpoints are explicitly loopback HTTP endpoints. This keeps a
              // tampered/stale ready file from turning the readiness probe into
              // a bearer-token exfiltration request.
              final identityUri = config.identityUri;
              if (!isExplicitLoopbackHttpEndpoint(config.baseUri) ||
                  identityUri == null ||
                  !isExplicitLoopbackHttpEndpoint(identityUri)) {
                continue;
              }

              // The ready file proves only that the child published ports. Do
              // not expose the Desktop UI until the identity endpoint accepts
              // this exact process token. This closes the publish-before-
              // serve_forever window and detects any accidental cross-process
              // readiness mix-up before the user can click Google.
              if (await _probeIdentityTransport(config)) {
                return config;
              }
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
      'Bundled local control plane did not become identity-ready',
    );
  }

  static Future<bool> _probeIdentityTransport(ControlPlaneConfig config) async {
    final identityUri = config.identityUri;
    if (identityUri == null) return false;

    final client = HttpClient()
      ..connectionTimeout = const Duration(milliseconds: 500);
    try {
      final request = await client
          .getUrl(identityUri.resolve('/v1/auth/providers'))
          .timeout(const Duration(milliseconds: 500));
      request.headers.set(
        HttpHeaders.authorizationHeader,
        'Bearer ${config.token}',
      );
      final response = await request.close().timeout(
            const Duration(milliseconds: 500),
          );
      await response.drain<void>().timeout(const Duration(milliseconds: 500));
      return response.statusCode == HttpStatus.ok;
    } on Object {
      return false;
    } finally {
      client.close(force: true);
    }
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
