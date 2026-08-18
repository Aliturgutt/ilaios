import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/reference_assets/reference_asset_draft.dart';

class _ReferenceTransport implements ControlPlaneTransport {
  final List<({String method, Uri uri, Map<String, String> headers, String? body})>
      requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'GET', uri: uri, headers: Map.of(headers), body: null));
    throw StateError('Unexpected GET ${uri.path}');
  }

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((method: 'POST', uri: uri, headers: Map.of(headers), body: body));
    if (uri.path == '/v1/reference-assets') {
      final payload = jsonDecode(body) as Map<String, dynamic>;
      final bytes = base64Decode(payload['content_base64'] as String);
      return ControlPlaneResponse(
        statusCode: 201,
        body: jsonEncode(<String, Object?>{
          'asset_id': 'ref-1234567890abcdef12345678',
          'sha256': payload['sha256'],
          'size_bytes': bytes.length,
          'mime_type': payload['mime_type'],
          'width': 64,
          'height': 48,
          'role': payload['role'],
        }),
      );
    }
    if (uri.path == '/v1/desktop/intent') {
      return const ControlPlaneResponse(
        statusCode: 201,
        body:
            '{"request_id":"exec-1","goal_id":"goal-1","job_id":"job-1","state":"PENDING","execution_status":"ADMITTED"}',
      );
    }
    throw StateError('Unexpected POST ${uri.path}');
  }
}

const _session = DesktopUserSession(
  sessionId: 'session-1',
  providerId: 'google',
  principalId: 'principal-1',
  tenantId: 'tenant-1',
);

ReferenceAssetDraft _draft(int index) {
  final bytes = Uint8List.fromList(<int>[137, 80, 78, 71, index]);
  return ReferenceAssetDraft(
    filename: 'reference-$index.png',
    mimeType: 'image/png',
    bytes: bytes,
    sha256Hex: sha256.convert(bytes).toString(),
    role: ReferenceAssetRoleDraft.product,
    instruction: 'Keep the product shape consistent.',
  );
}

void main() {
  setUp(ReferenceAssetSubmissionBus.clear);
  tearDown(ReferenceAssetSubmissionBus.clear);

  test('video references upload separately and intent carries immutable IDs only', () async {
    final transport = _ReferenceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_draft(1)]);

    final result = await client.submitPrompt(
      'Video creation task: Create a four-second product reveal.',
      _session,
    );

    expect(result.requestId, 'exec-1');
    expect(transport.requests, hasLength(2));
    final upload = transport.requests[0];
    final intent = transport.requests[1];
    expect(upload.uri.path, '/v1/reference-assets');
    expect(intent.uri.path, '/v1/desktop/intent');
    expect(upload.headers['X-ILAIOS-Session'], 'session-1');
    expect(intent.headers['X-ILAIOS-Session'], 'session-1');

    final uploadBody = jsonDecode(upload.body!) as Map<String, dynamic>;
    expect(uploadBody['content_base64'], isA<String>());
    expect(uploadBody['role'], 'product');
    expect(uploadBody['instruction'], 'Keep the product shape consistent.');

    final intentBody = jsonDecode(intent.body!) as Map<String, dynamic>;
    expect(intentBody['reference_asset_ids'], <String>['ref-1234567890abcdef12345678']);
    expect(intentBody.containsKey('content_base64'), isFalse);
    expect(intentBody.containsKey('bytes'), isFalse);
  });

  test('Web Factory references use the same upload and immutable-ID path', () async {
    final transport = _ReferenceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_draft(2)]);

    final result = await client.submitPrompt(
      'Build a premium website for my furniture company using this product reference.',
      _session,
    );

    expect(result.requestId, 'exec-1');
    expect(transport.requests, hasLength(2));
    expect(transport.requests[0].uri.path, '/v1/reference-assets');
    expect(transport.requests[1].uri.path, '/v1/desktop/intent');
    final intentBody =
        jsonDecode(transport.requests[1].body!) as Map<String, dynamic>;
    expect(intentBody['objective'], contains('website'));
    expect(intentBody['reference_asset_ids'], <String>['ref-1234567890abcdef12345678']);
    expect(intentBody.containsKey('content_base64'), isFalse);
    expect(intentBody.containsKey('bytes'), isFalse);
  });

  test('Web App dashboard references use the governed Web upload path', () async {
    final transport = _ReferenceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_draft(3)]);

    final result = await client.submitPrompt(
      'Build a Web App dashboard from these reference screenshots.',
      _session,
    );

    expect(result.requestId, 'exec-1');
    expect(transport.requests, hasLength(2));
    final intentBody =
        jsonDecode(transport.requests[1].body!) as Map<String, dynamic>;
    expect(intentBody['objective'], contains('Web App dashboard'));
    expect(intentBody['reference_asset_ids'], <String>['ref-1234567890abcdef12345678']);
  });

  test('Turkish Web App references are admitted without generic app widening', () async {
    final transport = _ReferenceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_draft(4)]);

    final result = await client.submitPrompt(
      'Bu referanslarla bir web uygulaması oluştur.',
      _session,
    );

    expect(result.requestId, 'exec-1');
    expect(transport.requests, hasLength(2));
  });

  test('references fail closed outside Web Factory and Video Factory', () async {
    final transport = _ReferenceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_draft(1)]);

    await expectLater(
      client.submitPrompt('Create a product image', _session),
      throwsA(
        isA<IdentityClientException>().having(
          (error) => error.message,
          'message',
          contains('Web Factory or Video Factory'),
        ),
      ),
    );
    expect(transport.requests, isEmpty);
  });

  test('generic mobile app references remain fail closed', () async {
    final transport = _ReferenceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_draft(5)]);

    await expectLater(
      client.submitPrompt('Build a mobile app from these screenshots', _session),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.requests, isEmpty);
  });

  test('more than twenty references are rejected before network upload', () async {
    final transport = _ReferenceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    ReferenceAssetSubmissionBus.replace(
      List<ReferenceAssetDraft>.generate(21, (index) => _draft(index + 1)),
    );

    await expectLater(
      client.submitPrompt('Video creation task: Make a launch clip.', _session),
      throwsA(
        isA<IdentityClientException>().having(
          (error) => error.message,
          'message',
          contains('at most 20'),
        ),
      ),
    );
    expect(transport.requests, isEmpty);
  });
}
