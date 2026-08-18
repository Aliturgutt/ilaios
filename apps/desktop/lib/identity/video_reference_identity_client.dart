import 'dart:convert';
import 'dart:io';
import 'dart:math';

import '../features/create/video_reference_picker.dart';
import 'identity_client.dart';

class VideoReferenceIdentityClient {
  VideoReferenceIdentityClient({
    required Uri baseUri,
    required String transportToken,
    HttpClient? httpClient,
  })  : _baseUri = _validateBaseUri(baseUri),
        _transportToken = _validateToken(transportToken),
        _httpClient = httpClient ?? HttpClient();

  final Uri _baseUri;
  final String _transportToken;
  final HttpClient _httpClient;

  Future<GovernedPromptSubmission> submitVideoPrompt(
    String objective,
    List<VideoReferenceDraft> references,
    DesktopUserSession session,
  ) async {
    final normalized = objective.trim();
    if (normalized.isEmpty || normalized.length > 20000) {
      throw const IdentityClientException('Video prompt is outside allowed bounds');
    }
    if (references.isEmpty || references.length > maxVideoReferenceImages) {
      throw const IdentityClientException(
        'Video reference count is outside allowed bounds',
      );
    }
    final digests = <String>{};
    var totalBytes = 0;
    for (final reference in references) {
      if (!digests.add(reference.sha256Digest)) {
        throw const IdentityClientException(
          'Duplicate video reference images are not allowed',
        );
      }
      if (reference.sizeBytes <= 0 ||
          reference.sizeBytes > maxVideoReferenceImageBytes) {
        throw const IdentityClientException(
          'A video reference image exceeds the 10 MiB limit',
        );
      }
      totalBytes += reference.sizeBytes;
    }
    if (totalBytes > maxVideoReferencePoolBytes) {
      throw const IdentityClientException(
        'Video reference images exceed the 40 MiB total limit',
      );
    }

    final draftId = _newDraftId();
    for (final reference in references) {
      await _uploadReference(draftId, reference, session);
    }
    final payload = await _postJson(
      '/v1/desktop/intent',
      <String, Object?>{
        'objective': normalized,
        'video_reference_draft_id': draftId,
      },
      session,
      expectedStatus: HttpStatus.created,
    );
    return _submission(payload);
  }

  Future<void> _uploadReference(
    String draftId,
    VideoReferenceDraft reference,
    DesktopUserSession session,
  ) async {
    final request = await _httpClient.postUrl(
      _baseUri.resolve('/v1/desktop/video-reference'),
    );
    request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $_transportToken');
    request.headers.set('X-ILAIOS-Session', session.sessionId);
    request.headers.set('X-ILAIOS-Video-Draft', draftId);
    request.headers.set('X-ILAIOS-Reference-Role', reference.role.wireValue);
    request.headers.contentType = ContentType.parse(reference.mediaType);
    request.contentLength = reference.sizeBytes;
    request.add(reference.bytes);
    final response = await request.close();
    final payload = await _decodeResponse(response);
    if (response.statusCode != HttpStatus.created) {
      throw IdentityClientException(_errorMessage(payload, 'Reference upload failed'));
    }
    if (payload['draft_id'] != draftId ||
        payload['sha256'] != reference.sha256Digest ||
        payload['size_bytes'] != reference.sizeBytes ||
        payload['role'] != reference.role.wireValue) {
      throw const IdentityClientException(
        'Reference upload acknowledgement does not match the local file',
      );
    }
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, Object?> body,
    DesktopUserSession session, {
    required int expectedStatus,
  }) async {
    final request = await _httpClient.postUrl(_baseUri.resolve(path));
    request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $_transportToken');
    request.headers.set('X-ILAIOS-Session', session.sessionId);
    request.headers.contentType = ContentType.json;
    final encoded = utf8.encode(jsonEncode(body));
    request.contentLength = encoded.length;
    request.add(encoded);
    final response = await request.close();
    final payload = await _decodeResponse(response);
    if (response.statusCode != expectedStatus) {
      throw IdentityClientException(
        _errorMessage(payload, 'Authenticated video submission failed'),
      );
    }
    return payload;
  }

  Future<Map<String, dynamic>> _decodeResponse(HttpClientResponse response) async {
    if (response.contentLength > 1024 * 1024) {
      throw const IdentityClientException('Identity response exceeds safe bounds');
    }
    final raw = await utf8.decoder.bind(response).join();
    if (raw.length > 1024 * 1024) {
      throw const IdentityClientException('Identity response exceeds safe bounds');
    }
    Object? decoded;
    try {
      decoded = jsonDecode(raw);
    } on FormatException {
      throw const IdentityClientException('Identity response is not valid JSON');
    }
    if (decoded is! Map<String, dynamic>) {
      throw const IdentityClientException('Identity response is malformed');
    }
    return decoded;
  }

  GovernedPromptSubmission _submission(Map<String, dynamic> payload) {
    final goalId = payload['goal_id'];
    final jobId = payload['job_id'];
    final state = payload['state'];
    final requestId = payload['request_id'];
    final executionStatus = payload['execution_status'];
    if (goalId is! String ||
        goalId.isEmpty ||
        jobId is! String ||
        jobId.isEmpty ||
        state is! String ||
        state.isEmpty ||
        requestId is! String ||
        requestId.isEmpty ||
        executionStatus is! String ||
        executionStatus.isEmpty) {
      throw const IdentityClientException(
        'Authenticated video intent response is malformed',
      );
    }
    return GovernedPromptSubmission(
      goalId: goalId,
      jobId: jobId,
      state: state,
      requestId: requestId,
      executionStatus: executionStatus,
    );
  }

  static String _errorMessage(Map<String, dynamic> payload, String fallback) {
    final error = payload['error'];
    return error is String && error.trim().isNotEmpty ? error.trim() : fallback;
  }

  static Uri _validateBaseUri(Uri value) {
    if (value.scheme != 'http' ||
        !{'127.0.0.1', 'localhost', '::1'}.contains(value.host) ||
        !value.hasPort) {
      throw ArgumentError('Video reference identity endpoint must be loopback HTTP');
    }
    return value;
  }

  static String _validateToken(String value) {
    final normalized = value.trim();
    if (normalized.isEmpty || normalized != value) {
      throw ArgumentError('Video reference transport token is invalid');
    }
    return normalized;
  }

  static String _newDraftId() {
    final random = Random.secure();
    final bytes = List<int>.generate(18, (_) => random.nextInt(256));
    final token = base64Url.encode(bytes).replaceAll('=', '');
    return 'video-draft-$token';
  }
}
