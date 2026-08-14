import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  test('packaged Desktop client talks to packaged authoritative runtime', () async {
    final sidecarPath = Platform.environment['ILAIOS_E2E_SIDECAR_PATH'];
    expect(
      sidecarPath,
      isNotNull,
      reason: 'Windows Gate must provide ILAIOS_E2E_SIDECAR_PATH',
    );
    final sidecar = File(sidecarPath!);
    expect(sidecar.existsSync(), isTrue, reason: 'Packaged sidecar must exist');

    final root = await Directory.systemTemp.createTemp('ilaios-desktop-e2e-');
    final readyFile = File('${root.path}${Platform.pathSeparator}ready.json');
    const token = 'desktop-e2e-runtime-token';
    final environment = Map<String, String>.from(Platform.environment)
      ..['ILAIOS_CONTROL_PLANE_TOKEN'] = token
      ..remove('ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON');

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
    unawaited(process.stdout.drain<void>());
    unawaited(process.stderr.drain<void>());
    addTearDown(() async {
      process.kill();
      try {
        await process.exitCode.timeout(const Duration(seconds: 5));
      } on TimeoutException {
        process.kill();
      }
      for (var attempt = 0; attempt < 30 && await root.exists(); attempt += 1) {
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
    for (var attempt = 0; attempt < 150; attempt += 1) {
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
    expect(ready, isNotNull, reason: 'Packaged Desktop runtime must publish readiness');
    final host = ready!['host'];
    final port = ready['port'];
    final identityHost = ready['identity_host'];
    final identityPort = ready['identity_port'];
    expect(host, isA<String>());
    expect(port, isA<int>());
    expect(identityHost, isA<String>());
    expect(identityPort, isA<int>());
    expect(ready['account_sign_in_configured'], isFalse);

    final controlPlaneUri = Uri(
      scheme: 'http',
      host: host as String,
      port: port as int,
    );
    final identityUri = Uri(
      scheme: 'http',
      host: identityHost as String,
      port: identityPort as int,
    );
    await _waitForReady(controlPlaneUri.resolve('/health/ready'));
    await _waitForReady(identityUri.resolve('/health/ready'));

    final client = ControlPlaneClient(baseUri: controlPlaneUri, token: token);
    final identity = IdentityClient(
      baseUri: identityUri,
      transportToken: token,
    );

    final providers = await identity.fetchProviders();
    final submission = await client.submitPrompt(
      'Build a deterministic Desktop E2E validation artifact',
    );
    final job = await client.fetchJob(submission.jobId);
    final projection = await client.fetchProjection();

    expect(providers, isEmpty);
    expect(submission.goalId, startsWith('goal-'));
    expect(submission.jobId, startsWith('job-'));
    expect(submission.state, 'PENDING');
    expect(job['goal_id'], submission.goalId);
    expect(job['state'], 'PENDING');
    expect(projection.connected, isTrue);
    expect(projection.goalCount, 1);
    expect(projection.jobCount, 1);
  }, timeout: const Timeout(Duration(seconds: 60)));
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
