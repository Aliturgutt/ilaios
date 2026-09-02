import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/knowledge/company_knowledge_client.dart';

class _FakeTransport implements ControlPlaneTransport {
  final List<({Uri uri, Map<String, String> headers, String body})> requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async => throw UnimplementedError();

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((uri: uri, headers: Map.of(headers), body: body));
    final payload = jsonDecode(body) as Map<String, dynamic>;
    return ControlPlaneResponse(
      statusCode: 201,
      body: jsonEncode(<String, Object?>{
        'source_id': 'company-file-0123456789abcdef0123456789abcdef',
        'latest_version': 1,
        'state': 'ACTIVE',
        'filename': payload['filename'],
        'mime_type': payload['mime_type'],
        'sha256': payload['sha256'],
        'knowledge_scope': 'company',
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
  test('uploads PDF through authenticated canonical company Knowledge boundary', () async {
    final directory = await Directory.systemTemp.createTemp('ilaios-company-knowledge-');
    addTearDown(() => directory.delete(recursive: true));
    final file = File('${directory.path}${Platform.pathSeparator}company.pdf');
    final bytes = <int>[0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x37];
    await file.writeAsBytes(bytes);
    final digest = sha256.convert(bytes).toString();
    final transport = _FakeTransport();
    final client = CompanyKnowledgeClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );

    final result = await client.uploadFile(file, _session);

    expect(result.sourceId, startsWith('company-file-'));
    expect(result.filename, 'company.pdf');
    expect(result.sha256Hex, digest);
    final request = transport.requests.single;
    expect(request.uri.path, '/v1/company-knowledge');
    expect(request.headers['Authorization'], 'Bearer local-transport-token');
    expect(request.headers['X-ILAIOS-Session'], 'session-1');
    final payload = jsonDecode(request.body) as Map<String, dynamic>;
    expect(payload['filename'], 'company.pdf');
    expect(payload['mime_type'], 'application/pdf');
    expect(payload['sha256'], digest);
    expect(base64Decode(payload['content_base64'] as String), bytes);
  });

  test('rejects unsupported local files before transport', () async {
    final directory = await Directory.systemTemp.createTemp('ilaios-company-knowledge-');
    addTearDown(() => directory.delete(recursive: true));
    final file = File('${directory.path}${Platform.pathSeparator}company.txt');
    await file.writeAsString('not supported');
    final transport = _FakeTransport();
    final client = CompanyKnowledgeClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );

    await expectLater(
      client.uploadFile(file, _session),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.requests, isEmpty);
  });
}
