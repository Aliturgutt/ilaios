import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/company_knowledge/company_knowledge_draft.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

void main() {
  tearDown(CompanyKnowledgeSubmissionBus.clear);

  test('uploads staged PDF to company Knowledge before intent and clears staging', () async {
    final bytes = Uint8List.fromList(<int>[0x25, 0x50, 0x44, 0x46, 0x2d, 0x31]);
    final digest = sha256.convert(bytes).toString();
    CompanyKnowledgeSubmissionBus.replace(<CompanyKnowledgeDraft>[
      CompanyKnowledgeDraft(
        filename: 'company.pdf',
        mimeType: 'application/pdf',
        bytes: bytes,
        sha256Hex: digest,
      ),
    ]);
    final transport = _RecordingTransport(digest);
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:7357/'),
      transportToken: 'transport-token',
      transport: transport,
    );
    const session = DesktopUserSession(
      sessionId: 'session-1',
      providerId: 'google',
      principalId: 'user-1',
      tenantId: 'tenant-1',
    );

    final result = await client.submitPrompt('Build a report', session);

    expect(result.goalId, 'goal-1');
    expect(transport.paths, <String>['/v1/company-knowledge', '/v1/desktop/intent']);
    expect(CompanyKnowledgeSubmissionBus.pending, isEmpty);
    final companyBody = transport.bodies.first;
    expect(companyBody['filename'], 'company.pdf');
    expect(companyBody['sha256'], digest);
    expect(companyBody['content_base64'], base64Encode(bytes));
    expect(transport.headers.first['X-ILAIOS-Session'], 'session-1');
  });

  test('rejects duplicate staged company document content before transport', () async {
    final bytes = Uint8List.fromList(<int>[0x25, 0x50, 0x44, 0x46, 0x2d]);
    final digest = sha256.convert(bytes).toString();
    final draft = CompanyKnowledgeDraft(
      filename: 'company.pdf',
      mimeType: 'application/pdf',
      bytes: bytes,
      sha256Hex: digest,
    );
    CompanyKnowledgeSubmissionBus.replace(<CompanyKnowledgeDraft>[draft, draft]);
    final transport = _RecordingTransport(digest);
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:7357/'),
      transportToken: 'transport-token',
      transport: transport,
    );
    const session = DesktopUserSession(
      sessionId: 'session-1',
      providerId: 'google',
      principalId: 'user-1',
      tenantId: 'tenant-1',
    );

    await expectLater(
      client.submitPrompt('Build a report', session),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.paths, isEmpty);
  });
}

class _RecordingTransport implements ControlPlaneTransport {
  _RecordingTransport(this.digest);

  final String digest;
  final List<String> paths = <String>[];
  final List<Map<String, dynamic>> bodies = <Map<String, dynamic>>[];
  final List<Map<String, String>> headers = <Map<String, String>>[];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async => const ControlPlaneResponse(statusCode: 404, body: '{}');

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    paths.add(uri.path);
    bodies.add(jsonDecode(body) as Map<String, dynamic>);
    this.headers.add(Map<String, String>.from(headers));
    if (uri.path == '/v1/company-knowledge') {
      return ControlPlaneResponse(
        statusCode: 201,
        body: jsonEncode(<String, Object?>{
          'source_id': 'company-file-0123456789abcdef0123456789abcdef',
          'latest_version': 1,
          'state': 'ACTIVE',
          'filename': 'company.pdf',
          'mime_type': 'application/pdf',
          'sha256': digest,
          'knowledge_scope': 'company',
        }),
      );
    }
    if (uri.path == '/v1/desktop/intent') {
      return ControlPlaneResponse(
        statusCode: 201,
        body: jsonEncode(<String, Object?>{
          'goal_id': 'goal-1',
          'job_id': 'job-1',
          'state': 'created',
          'request_id': 'request-1',
          'execution_status': 'ADMITTED',
          'business_context_code': null,
        }),
      );
    }
    return const ControlPlaneResponse(statusCode: 404, body: '{}');
  }
}
