import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';

class _RefinementTransport implements ControlPlaneTransport {
  final List<({Uri uri, Map<String, String> headers, String body})> requests = [];

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async => throw StateError('GET not expected');

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    requests.add((uri: uri, headers: Map.of(headers), body: body));
    return const ControlPlaneResponse(
      statusCode: 200,
      body: '{'
          '"original_prompt":"Build a website. Never deploy to production.",'
          '"refined_prompt":"Objective: Build a website.\\nConstraints:\\n- Never deploy to production.",'
          '"mode":"structure",'
          '"transformed":true,'
          '"detected_issues":[],'
          '"preserved_constraints":["Never deploy to production."],'
          '"unresolved_ambiguities":[],'
          '"warnings":[],'
          '"evaluation":{'
          '"constraints_detected":true,'
          '"risk_cues":["production"],'
          '"risk_cues_preserved":true'
          '}'
          '}',
    );
  }
}

void main() {
  test('refinement preview is authenticated and never submits work', () async {
    final transport = _RefinementTransport();
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    final preview = await client.refinePrompt(
      'Build a website. Never deploy to production.',
      PromptRefinementMode.structure,
    );

    expect(preview.mode, PromptRefinementMode.structure);
    expect(preview.transformed, isTrue);
    expect(preview.preservedConstraints, ['Never deploy to production.']);
    expect(preview.riskCues, ['production']);
    expect(preview.riskCuesPreserved, isTrue);
    expect(transport.requests, hasLength(1));
    final request = transport.requests.single;
    expect(request.uri.path, '/v1/prompts/refine');
    expect(request.headers['Authorization'], 'Bearer runtime-secret');
    expect(jsonDecode(request.body), <String, dynamic>{
      'prompt': 'Build a website. Never deploy to production.',
      'mode': 'structure',
    });
  });

  test('refinement rejects malformed preservation evidence', () async {
    final transport = _MalformedRefinementTransport();
    final client = ControlPlaneClient(
      baseUri: Uri.parse('http://127.0.0.1:4123'),
      token: 'runtime-secret',
      transport: transport,
    );

    await expectLater(
      client.refinePrompt('Build a website', PromptRefinementMode.improve),
      throwsA(isA<ControlPlaneClientException>()),
    );
  });
}

class _MalformedRefinementTransport implements ControlPlaneTransport {
  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async => throw StateError('GET not expected');

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async => const ControlPlaneResponse(
        statusCode: 200,
        body: '{'
            '"original_prompt":"Build a website",'
            '"refined_prompt":"Build a website",'
            '"mode":"improve",'
            '"transformed":false,'
            '"detected_issues":[],'
            '"preserved_constraints":[],'
            '"unresolved_ambiguities":[],'
            '"warnings":[],'
            '"evaluation":{'
            '"constraints_detected":false,'
            '"risk_cues":[],'
            '"risk_cues_preserved":"yes"'
            '}'
            '}',
      );
}
