import 'dart:convert';
import 'dart:io';

import '../control_plane/client.dart';
import '../reference_assets/reference_attachment.dart';
import 'identity_client_core.dart' as core;

export 'identity_client_core.dart' hide IdentityClient;

class IdentityClient extends core.IdentityClient {
  // The same constructor inputs also initialize the local reference transport,
  // so keeping named locals is intentional instead of converting to super params.
  // ignore: use_super_parameters
  IdentityClient({
    required Uri baseUri,
    required String transportToken,
    ControlPlaneTransport? transport,
    core.IdentityRetryDelay? retryDelay,
  })  : _referenceBaseUri = baseUri,
        _referenceTransportToken = transportToken,
        _referenceTransport = transport ??
            const IoControlPlaneTransport(timeout: Duration(seconds: 30)),
        super(
          baseUri: baseUri,
          transportToken: transportToken,
          transport: transport,
          retryDelay: retryDelay,
        );

  final Uri _referenceBaseUri;
  final String _referenceTransportToken;
  final ControlPlaneTransport _referenceTransport;

  @override
  Future<core.GovernedPromptSubmission> submitPrompt(
    String objective,
    core.DesktopUserSession session,
  ) async {
    final attachments = currentReferenceAttachments;
    if (attachments.isEmpty) {
      return super.submitPrompt(objective, session);
    }
    final normalized = objective.trim();
    if (normalized.isEmpty) {
      throw const core.IdentityClientException('Prompt must not be empty');
    }
    if (normalized.length > 20000) {
      throw const core.IdentityClientException(
        'Prompt exceeds the Desktop input limit',
      );
    }

    final assetIds = <String>[];
    for (final attachment in attachments) {
      final payload = await _sessionPost(
        '/v1/desktop/reference-assets',
        <String, Object?>{
          'filename': attachment.originalName,
          'media_type': attachment.mediaType,
          'sha256': attachment.sha256,
          'content_base64': base64Encode(attachment.bytes),
        },
        'reference image upload',
        session,
        expectedStatus: HttpStatus.created,
      );
      final assetId = payload['asset_id'];
      final returnedDigest = payload['sha256'];
      if (assetId is! String ||
          assetId.isEmpty ||
          returnedDigest != attachment.sha256) {
        throw const core.IdentityClientException(
          'Reference image upload response is malformed',
        );
      }
      assetIds.add(assetId);
    }

    final payload = await _sessionPost(
      '/v1/desktop/intent',
      <String, Object?>{
        'objective': normalized,
        'reference_asset_ids': assetIds,
      },
      'authenticated intent with reference images',
      session,
      expectedStatus: HttpStatus.created,
    );
    final goalId = payload['goal_id'];
    final jobId = payload['job_id'];
    final state = payload['state'];
    final requestId = payload['request_id'];
    final executionStatus = payload['execution_status'];
    final referenceAssetCount = payload['reference_asset_count'];
    if (goalId is! String ||
        goalId.isEmpty ||
        jobId is! String ||
        jobId.isEmpty ||
        state is! String ||
        state.isEmpty ||
        requestId is! String ||
        requestId.isEmpty ||
        executionStatus is! String ||
        executionStatus.isEmpty ||
        referenceAssetCount != assetIds.length) {
      throw const core.IdentityClientException(
        'Authenticated reference intent response is malformed',
      );
    }
    return core.GovernedPromptSubmission(
      goalId: goalId,
      jobId: jobId,
      state: state,
      requestId: requestId,
      executionStatus: executionStatus,
    );
  }

  Future<Map<String, dynamic>> _sessionPost(
    String path,
    Map<String, Object?> body,
    String label,
    core.DesktopUserSession session, {
    required int expectedStatus,
  }) async {
    final response = await _referenceTransport.post(
      _referenceBaseUri.resolve(path),
      body: jsonEncode(body),
      headers: <String, String>{
        'Authorization': 'Bearer $_referenceTransportToken',
        'X-ILAIOS-Session': session.sessionId,
      },
    );
    Map<String, dynamic> payload;
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException();
      }
      payload = decoded;
    } on FormatException {
      throw core.IdentityClientException(
        'Desktop $label response is malformed',
      );
    }
    if (response.statusCode == HttpStatus.unauthorized ||
        response.statusCode == HttpStatus.forbidden) {
      throw const core.IdentityClientException(
        'Desktop authenticated session is invalid',
      );
    }
    if (response.statusCode != expectedStatus) {
      final error = payload['error'];
      if (error is String && error.isNotEmpty) {
        throw core.IdentityClientException(error);
      }
      throw core.IdentityClientException('Desktop $label failed');
    }
    return payload;
  }
}
