import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/reference_assets/reference_asset_draft.dart';
import 'package:ilaios_desktop/source_media/source_media_draft.dart';

class _SourceTransport implements ControlPlaneTransport {
  _SourceTransport({this.failIntent = false});

  final bool failIntent;
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
    if (uri.path == '/v1/source-media') {
      final payload = jsonDecode(body) as Map<String, dynamic>;
      final bytes = base64Decode(payload['content_base64'] as String);
      return ControlPlaneResponse(
        statusCode: 201,
        body: jsonEncode(<String, Object?>{
          'asset_id': 'src-1234567890abcdef12345678',
          'sha256': payload['sha256'],
          'size_bytes': bytes.length,
          'mime_type': 'video/mp4',
          'duration_seconds': 12.0,
          'width': 1920,
          'height': 1080,
        }),
      );
    }
    if (uri.path == '/v1/source-media/discard') {
      return const ControlPlaneResponse(
        statusCode: 200,
        body:
            '{"discarded":true,"asset_id":"src-1234567890abcdef12345678"}',
      );
    }
    if (uri.path == '/v1/desktop/intent') {
      if (failIntent) {
        return const ControlPlaneResponse(
          statusCode: 400,
          body: '{"error":"simulated intent rejection"}',
        );
      }
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

SourceMediaDraft _source() {
  final bytes = Uint8List.fromList(<int>[
    0x00,
    0x00,
    0x00,
    0x18,
    0x66,
    0x74,
    0x79,
    0x70,
    0x69,
    0x73,
    0x6f,
    0x6d,
    1,
    2,
    3,
  ]);
  return SourceMediaDraft(
    filename: 'source.mp4',
    bytes: bytes,
    sha256Hex: sha256.convert(bytes).toString(),
  );
}

ReferenceAssetDraft _reference() {
  final bytes = Uint8List.fromList(<int>[137, 80, 78, 71, 1]);
  return ReferenceAssetDraft(
    filename: 'reference.png',
    mimeType: 'image/png',
    bytes: bytes,
    sha256Hex: sha256.convert(bytes).toString(),
  );
}

void main() {
  setUp(() {
    SourceMediaSubmissionBus.clear();
    ReferenceAssetSubmissionBus.clear();
  });
  tearDown(() {
    SourceMediaSubmissionBus.clear();
    ReferenceAssetSubmissionBus.clear();
  });

  test('source video uploads separately and intent carries immutable src ID only', () async {
    final transport = _SourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    SourceMediaSubmissionBus.replace(_source());

    final result = await client.submitPrompt(
      'Video creation task: Edit this video and shorten the ending.',
      _session,
    );

    expect(result.requestId, 'exec-1');
    expect(transport.requests, hasLength(2));
    expect(transport.requests[0].uri.path, '/v1/source-media');
    expect(transport.requests[1].uri.path, '/v1/desktop/intent');
    final uploadBody =
        jsonDecode(transport.requests[0].body!) as Map<String, dynamic>;
    final intentBody =
        jsonDecode(transport.requests[1].body!) as Map<String, dynamic>;
    expect(uploadBody['content_base64'], isA<String>());
    expect(uploadBody['mime_type'], 'video/mp4');
    expect(intentBody['source_media_asset_id'], 'src-1234567890abcdef12345678');
    expect(intentBody['reference_asset_ids'], isEmpty);
    expect(intentBody.containsKey('content_base64'), isFalse);
    expect(intentBody.containsKey('bytes'), isFalse);
    expect(transport.requests[0].headers['X-ILAIOS-Session'], 'session-1');
  });

  test('source video fails closed outside Video Factory before upload', () async {
    final transport = _SourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    SourceMediaSubmissionBus.replace(_source());

    await expectLater(
      client.submitPrompt('Website build task: Build a premium website.', _session),
      throwsA(
        isA<IdentityClientException>().having(
          (error) => error.message,
          'message',
          contains('Video Factory'),
        ),
      ),
    );
    expect(transport.requests, isEmpty);
  });

  test('source video and image references fail before any network side effect', () async {
    final transport = _SourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    SourceMediaSubmissionBus.replace(_source());
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_reference()]);

    await expectLater(
      client.submitPrompt(
        'Video creation task: Edit this video using the reference.',
        _session,
      ),
      throwsA(
        isA<IdentityClientException>().having(
          (error) => error.message,
          'message',
          contains('cannot be combined'),
        ),
      ),
    );
    expect(transport.requests, isEmpty);
  });

  test('failed intent triggers best-effort discard of unbound uploaded source', () async {
    final transport = _SourceTransport(failIntent: true);
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    SourceMediaSubmissionBus.replace(_source());

    await expectLater(
      client.submitPrompt(
        'Video creation task: Edit this video and shorten the ending.',
        _session,
      ),
      throwsA(isA<IdentityClientException>()),
    );
    expect(
      transport.requests.map((request) => request.uri.path).toList(),
      <String>[
        '/v1/source-media',
        '/v1/desktop/intent',
        '/v1/source-media/discard',
      ],
    );
  });
}
