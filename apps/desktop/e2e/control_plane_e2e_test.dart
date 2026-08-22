import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  test('packaged Desktop client talks to packaged authoritative runtime', () async {
    final sidecarPath = Platform.environment['ILAIOS_E2E_SIDECAR_PATH'];
    final expectedSourceHead = Platform.environment['ILAIOS_E2E_SOURCE_SHA'];
    expect(
      sidecarPath,
      isNotNull,
      reason: 'Windows Gate must provide ILAIOS_E2E_SIDECAR_PATH',
    );
    expect(
      expectedSourceHead,
      isNotNull,
      reason: 'Windows Gate must provide ILAIOS_E2E_SOURCE_SHA',
    );
    final sidecar = File(sidecarPath!);
    expect(sidecar.existsSync(), isTrue, reason: 'Packaged sidecar must exist');

    final root = await Directory.systemTemp.createTemp('ilaios-desktop-e2e-');
    final readyFile = File('${root.path}${Platform.pathSeparator}ready.json');
    const token = 'placeholder-desktop-e2e-token';
    final environment = Map<String, String>.from(Platform.environment)
      ..['ILAIOS_CONTROL_PLANE_TOKEN'] = token
      ..remove('ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON')
      ..remove('OPENROUTER_API_KEY');

    final startup = Stopwatch()..start();
    final process = await Process.start(
      sidecar.path,
      <String>[
        '--data-root',
        root.path,
        '--ready-file',
        readyFile.path,
      ],
      environment: environment,
    );
    final stdoutBuffer = StringBuffer();
    final stderrBuffer = StringBuffer();
    final stdoutSubscription = process.stdout
        .transform(utf8.decoder)
        .listen(stdoutBuffer.write);
    final stderrSubscription = process.stderr
        .transform(utf8.decoder)
        .listen(stderrBuffer.write);
    Uri? identityUri;
    addTearDown(() async {
      var exited = false;
      final shutdownBase = identityUri;
      if (shutdownBase != null) {
        try {
          await _requestShutdown(shutdownBase, token);
          await process.exitCode.timeout(const Duration(seconds: 5));
          exited = true;
        } on Object {
          // The parent-pipe EOF path below is the bounded graceful fallback.
        }
      }
      if (!exited) {
        try {
          await process.stdin.close();
        } on Object {
          // The pipe may already be closed if the child started exiting.
        }
        try {
          await process.exitCode.timeout(const Duration(seconds: 3));
          exited = true;
        } on TimeoutException {
          // Forced termination is the final bounded fallback, never the proof path.
        }
      }
      if (!exited) {
        process.kill();
        try {
          await process.exitCode.timeout(const Duration(seconds: 3));
        } on TimeoutException {
          // The directory-release assertion below remains authoritative.
        }
      }
      await stdoutSubscription.cancel();
      await stderrSubscription.cancel();
      for (var attempt = 0; attempt < 50 && await root.exists(); attempt += 1) {
        try {
          await root.delete(recursive: true);
        } on FileSystemException {
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
      }
      expect(
        await root.exists(),
        isFalse,
        reason: 'Packaged runtime must release its data directory on shutdown',
      );
    });

    Map<String, dynamic>? ready;
    // PyInstaller --onefile performs a bounded cold extraction before Python can
    // publish readiness. The packaged runtime diagnostic already certifies a
    // 60-second bound; use that same fail-closed product contract here while
    // retaining exact startup-latency evidence.
    for (var attempt = 0; attempt < 600; attempt += 1) {
      if (await readyFile.exists()) {
        try {
          final decoded = jsonDecode(await readyFile.readAsString());
          if (decoded is Map<String, dynamic>) {
            ready = decoded;
            break;
          }
        } on FormatException {
          // Retry while the readiness file is being written.
        }
      }
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }
    startup.stop();
    if (ready == null) {
      int? exitCode;
      try {
        exitCode = await process.exitCode.timeout(const Duration(milliseconds: 100));
      } on TimeoutException {
        // A still-running process is useful failure evidence too.
      }
      fail(
        'Packaged Desktop runtime must publish readiness within 60 seconds. '
        'startup_ms=${startup.elapsedMilliseconds}; '
        'exit_code=${exitCode ?? 'running'}; '
        'stdout=${stdoutBuffer.toString()}; '
        'stderr=${stderrBuffer.toString()}',
      );
    }
    // Keep the measured packaged cold-start latency in CI output as evidence.
    // ignore: avoid_print
    print('ILAIOS_PACKAGED_READY_LATENCY_MS=${startup.elapsedMilliseconds}');

    final host = ready['host'];
    final port = ready['port'];
    final identityHost = ready['identity_host'];
    final identityPort = ready['identity_port'];
    expect(host, isA<String>());
    expect(port, isA<int>());
    expect(identityHost, isA<String>());
    expect(identityPort, isA<int>());
    expect(ready['account_sign_in_configured'], isTrue);
    // This generic packaging gate deliberately strips provider credentials.
    // Readiness must therefore fail closed instead of pretending cinematic
    // generation is configured. Credentialed provider proof runs separately.
    expect(ready['video_finished_product_configured'], isFalse);
    expect(ready['video_provider'], 'unavailable');
    expect(ready['web_finished_product_configured'], isTrue);
    expect(ready['software_finished_product_configured'], isTrue);
    expect(ready['execution_recovery_configured'], isTrue);
    expect(ready['source_head_sha'], expectedSourceHead);

    final controlPlaneUri = Uri(
      scheme: 'http',
      host: host as String,
      port: port as int,
    );
    final readyIdentityUri = Uri(
      scheme: 'http',
      host: identityHost as String,
      port: identityPort as int,
    );
    identityUri = readyIdentityUri;
    await _waitForReady(controlPlaneUri.resolve('/health/ready'));
    await _waitForReady(readyIdentityUri.resolve('/health/ready'));

    final client = ControlPlaneClient(baseUri: controlPlaneUri, token: token);
    final identity = IdentityClient(
      baseUri: readyIdentityUri,
      transportToken: token,
    );

    final providers = await identity.fetchProviders();
    final submission = await client.submitPrompt(
      'Build a deterministic Desktop E2E validation artifact',
    );
    final job = await client.fetchJob(submission.jobId);
    final projection = await client.fetchProjection();

    expect(providers, hasLength(1));
    expect(providers.single.providerId, 'google');
    expect(providers.single.displayName, 'Google');
    expect(submission.goalId, startsWith('goal-'));
    expect(submission.jobId, startsWith('job-'));
    expect(submission.state, 'PENDING');
    expect(job['goal_id'], submission.goalId);
    expect(job['state'], 'PENDING');
    expect(projection.connected, isTrue);
    expect(projection.goalCount, 1);
    expect(projection.jobCount, 1);
  }, timeout: const Timeout(Duration(seconds: 105)));
}

Future<void> _requestShutdown(Uri baseUri, String token) async {
  final client = HttpClient();
  try {
    final request = await client
        .postUrl(baseUri.resolve('/v1/runtime/shutdown'))
        .timeout(const Duration(seconds: 1));
    request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
    request.headers.contentType = ContentType.json;
    final body = utf8.encode('{}');
    request.contentLength = body.length;
    request.add(body);
    final response = await request.close().timeout(const Duration(seconds: 1));
    await response.drain<void>().timeout(const Duration(seconds: 1));
    if (response.statusCode != HttpStatus.accepted) {
      throw StateError('Packaged runtime rejected graceful shutdown');
    }
  } finally {
    client.close(force: true);
  }
}

Future<void> _waitForReady(Uri uri) async {
  final client = HttpClient();
  try {
    Object? lastError;
    for (var attempt = 0; attempt < 150; attempt += 1) {
      try {
        final request = await client.getUrl(uri).timeout(
          const Duration(milliseconds: 500),
        );
        final response = await request.close().timeout(
          const Duration(milliseconds: 500),
        );
        final body = await utf8.decoder.bind(response).join();
        if (response.statusCode == HttpStatus.ok) {
          final decoded = jsonDecode(body);
          if (decoded is Map<String, dynamic> && decoded['status'] == 'ready') {
            return;
          }
        }
        lastError = StateError(
          'health endpoint returned ${response.statusCode}: $body',
        );
      } on Object catch (error) {
        lastError = error;
      }
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }
    throw StateError('Runtime never became ready at $uri: $lastError');
  } finally {
    client.close(force: true);
  }
}
