import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/factory_selection/factory_selection.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

class _IntentTransport implements ControlPlaneTransport {
  _IntentTransport(this.resolvedId);
  final String resolvedId;
  Map<String, dynamic>? sent;
  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const {},
  }) async => throw StateError('Unexpected GET');
  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const {},
  }) async {
    expect(uri.path, '/v1/desktop/intent');
    sent = jsonDecode(body) as Map<String, dynamic>;
    return ControlPlaneResponse(
      statusCode: 201,
      body: jsonEncode({
        'request_id': 'request-1',
        'goal_id': 'goal-1',
        'job_id': 'job-1',
        'state': 'PENDING',
        'execution_status': 'ADMITTED',
        'selected_factory_id': sent!['selected_factory_id'],
        'resolved_factory_id': resolvedId,
      }),
    );
  }
}

const _session = DesktopUserSession(
  sessionId: 'session-1',
  providerId: 'google',
  principalId: 'principal-1',
  tenantId: 'tenant-1',
);

void main() {
  test('exactly nine canonical factory IDs and one-shot staging', () {
    expect(DesktopFactorySelection.ids.length, 9);
    expect(DesktopFactorySelection.ids.toSet().length, 9);
    for (final id in DesktopFactorySelection.ids) {
      expect(DesktopFactorySelection.valid(id), isTrue);
      FactorySelectionSubmissionBus.stage(id);
      expect(FactorySelectionSubmissionBus.take(), id);
      expect(FactorySelectionSubmissionBus.take(), isNull);
    }
    expect(
      () => FactorySelectionSubmissionBus.stage('invented'),
      throwsArgumentError,
    );
  });

  for (final id in DesktopFactorySelection.ids) {
    test('sends and verifies selected factory: $id', () async {
      final transport = _IntentTransport(id);
      final client = IdentityClient(
        baseUri: Uri.parse('http://127.0.0.1:43123'),
        transportToken: 'local-transport-token',
        transport: transport,
      );
      await client.submitPrompt(
        'Factory task',
        _session,
        selectedFactoryId: id,
      );
      expect(transport.sent!['selected_factory_id'], id);
    });
  }

  test('rejects mismatched resolved factory response', () async {
    final transport = _IntentTransport(DesktopFactorySelection.ids[1]);
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    await expectLater(
      client.submitPrompt(
        'Factory task',
        _session,
        selectedFactoryId: DesktopFactorySelection.ids[0],
      ),
      throwsA(isA<IdentityClientException>()),
    );
  });

  test('rejects unknown factory before transport', () async {
    final transport = _IntentTransport('invented');
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    await expectLater(
      client.submitPrompt(
        'Factory task',
        _session,
        selectedFactoryId: 'invented',
      ),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.sent, isNull);
  });
}
