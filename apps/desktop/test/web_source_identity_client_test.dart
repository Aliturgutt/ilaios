import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/reference_assets/reference_asset_draft.dart';
import 'package:ilaios_desktop/source_media/source_media_draft.dart';
import 'package:ilaios_desktop/web_source/web_source_draft.dart';

class _WebSourceTransport implements ControlPlaneTransport {
  _WebSourceTransport({this.failIntent = false});

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
    if (uri.path == '/v1/web-source') {
      final payload = jsonDecode(body) as Map<String, dynamic>;
      final bytes = base64Decode(payload['content_base64'] as String);
      return ControlPlaneResponse(
        statusCode: 201,
        body: jsonEncode(<String, Object?>{
          'asset_id': 'wsrc-1234567890abcdef12345678',
          'archive_sha256': payload['sha256'],
          'tree_sha256': 'a' * 64,
          'size_bytes': bytes.length,
          'framework': 'nextjs-react',
          'router': 'app-router',
          'routes': <String>['/'],
          'file_count': 2,
        }),
      );
    }
    if (uri.path == '/v1/web-source/discard') {
      return const ControlPlaneResponse(
        statusCode: 200,
        body:
            '{"discarded":true,"asset_id":"wsrc-1234567890abcdef12345678"}',
      );
    }
    if (uri.path == '/v1/reference-assets') {
      final payload = jsonDecode(body) as Map<String, dynamic>;
      final bytes = base64Decode(payload['content_base64'] as String);
      return ControlPlaneResponse(
        statusCode: 201,
        body: jsonEncode(<String, Object?>{
          'asset_id': 'ref-1234567890abcdef12345678',
          'sha256': payload['sha256'],
          'size_bytes': bytes.length,
        }),
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

WebSourceDraft _webSource() {
  final bytes = Uint8List.fromList(<int>[
    0x50,
    0x4b,
    0x03,
    0x04,
    1,
    2,
    3,
    4,
  ]);
  return WebSourceDraft(
    filename: 'existing-site.zip',
    bytes: bytes,
    sha256Hex: sha256.convert(bytes).toString(),
  );
}

SourceMediaDraft _videoSource() {
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
    WebSourceSubmissionBus.clear();
    SourceMediaSubmissionBus.clear();
    ReferenceAssetSubmissionBus.clear();
  });
  tearDown(() {
    WebSourceSubmissionBus.clear();
    SourceMediaSubmissionBus.clear();
    ReferenceAssetSubmissionBus.clear();
  });

  test('existing Web source uploads separately and intent carries immutable wsrc ID', () async {
    final transport = _WebSourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    WebSourceSubmissionBus.replace(_webSource());

    final result = await client.submitPrompt(
      'Upgrade this Web App dashboard while preserving its existing source.',
      _session,
    );

    expect(result.requestId, 'exec-1');
    expect(transport.requests, hasLength(2));
    expect(transport.requests[0].uri.path, '/v1/web-source');
    expect(transport.requests[1].uri.path, '/v1/desktop/intent');
    expect(transport.requests[0].headers['X-ILAIOS-Session'], 'session-1');
    expect(transport.requests[1].headers['X-ILAIOS-Session'], 'session-1');
    final upload = jsonDecode(transport.requests[0].body!) as Map<String, dynamic>;
    final intent = jsonDecode(transport.requests[1].body!) as Map<String, dynamic>;
    expect(upload['content_base64'], isA<String>());
    expect(intent['web_source_asset_id'], 'wsrc-1234567890abcdef12345678');
    expect(intent.containsKey('content_base64'), isFalse);
    expect(intent.containsKey('bytes'), isFalse);
  });

  test('existing Web source can be combined with Web reference screenshots', () async {
    final transport = _WebSourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    WebSourceSubmissionBus.replace(_webSource());
    ReferenceAssetSubmissionBus.replace(<ReferenceAssetDraft>[_reference()]);

    await client.submitPrompt(
      'Upgrade this Web App dashboard to match the reference screenshot.',
      _session,
    );

    expect(
      transport.requests.map((request) => request.uri.path).toList(),
      <String>['/v1/reference-assets', '/v1/web-source', '/v1/desktop/intent'],
    );
    final intent = jsonDecode(transport.requests.last.body!) as Map<String, dynamic>;
    expect(intent['reference_asset_ids'], <String>['ref-1234567890abcdef12345678']);
    expect(intent['web_source_asset_id'], 'wsrc-1234567890abcdef12345678');
  });

  test('existing Web source fails closed for Video Factory before upload', () async {
    final transport = _WebSourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    WebSourceSubmissionBus.replace(_webSource());

    await expectLater(
      client.submitPrompt('Video creation task: Make a short launch clip.', _session),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.requests, isEmpty);
  });

  test('existing Web source and source video fail before network side effects', () async {
    final transport = _WebSourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    WebSourceSubmissionBus.replace(_webSource());
    SourceMediaSubmissionBus.replace(_videoSource());

    await expectLater(
      client.submitPrompt('Build a Web App dashboard from the existing source.', _session),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.requests, isEmpty);
  });

  test('failed intent triggers best-effort discard of uploaded Web source', () async {
    final transport = _WebSourceTransport(failIntent: true);
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    WebSourceSubmissionBus.replace(_webSource());

    await expectLater(
      client.submitPrompt(
        'Upgrade this Web App dashboard from its existing source.',
        _session,
      ),
      throwsA(isA<IdentityClientException>()),
    );

    expect(
      transport.requests.map((request) => request.uri.path).toList(),
      <String>['/v1/web-source', '/v1/desktop/intent', '/v1/web-source/discard'],
    );
  });

  test('invalid local Web source digest fails before network upload', () async {
    final transport = _WebSourceTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-transport-token',
      transport: transport,
    );
    final source = _webSource();
    WebSourceSubmissionBus.replace(
      WebSourceDraft(
        filename: source.filename,
        bytes: source.bytes,
        sha256Hex: 'not-a-digest',
      ),
    );

    await expectLater(
      client.submitPrompt('Build a Web App dashboard from this source.', _session),
      throwsA(isA<IdentityClientException>()),
    );
    expect(transport.requests, isEmpty);
  });
}
