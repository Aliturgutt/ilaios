import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';

class _ClarificationTransport implements ControlPlaneTransport {
  final List<Uri> posted = <Uri>[];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async {
    throw StateError('Unexpected GET $uri');
  }

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    posted.add(uri);
    if (uri.path == '/v1/goals') {
      return const ControlPlaneResponse(
        statusCode: 400,
        body:
            '{"error":"clarification required: Bu alternatiflerden hangisi ana çıktı olmalı: video, web?"}',
      );
    }
    throw StateError('Unexpected POST $uri');
  }
}

void main() {
  test('surfaces bounded clarification and does not create a job', () async {
    final transport = _ClarificationTransport();
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    await expectLater(
      client.submitPrompt('web sitesi veya video yap'),
      throwsA(
        isA<ControlPlaneClientException>().having(
          (error) => error.message,
          'message',
          contains('hangisi ana çıktı olmalı'),
        ),
      ),
    );

    expect(transport.posted, hasLength(1));
    expect(transport.posted.single.path, '/v1/goals');
  });
}
