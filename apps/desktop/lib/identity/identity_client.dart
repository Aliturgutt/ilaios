export 'identity_client_core.dart' hide IdentityClient;

import 'dart:convert';
import 'dart:io';

import '../control_plane/client.dart';
import '../reference_assets/reference_asset_draft.dart';
import 'identity_client_core.dart' as core;

/// Backward-compatible IdentityClient that extends the existing authenticated
/// session client with the shared Web/Video reference-asset submission contract.
/// All non-reference auth/session behavior remains delegated to the canonical
/// implementation in [core.IdentityClient].
class IdentityClient extends core.IdentityClient {
  factory IdentityClient({
    required Uri baseUri,
    required String transportToken,
    ControlPlaneTransport? transport,
    core.IdentityRetryDelay? retryDelay,
  }) {
    final resolvedTransport = transport ?? const IoControlPlaneTransport();
    return IdentityClient._(
      baseUri: baseUri,
      transportToken: transportToken,
      transport: resolvedTransport,
      retryDelay: retryDelay,
    );
  }

  IdentityClient._({
    required Uri baseUri,
    required String transportToken,
    required ControlPlaneTransport transport,
    core.IdentityRetryDelay? retryDelay,
  })  : _referenceBaseUri = baseUri,
        _referenceTransportToken = transportToken,
        _referenceTransport = transport,
        super(
          baseUri: baseUri,
          transportToken: transportToken,
          transport: transport,
          retryDelay: retryDelay,
        );

  static const int _maxReferenceAssets = 20;
  static const int _maxReferenceAssetBytes = 10 * 1024 * 1024;
  static const int _maxReferenceTotalBytes = 100 * 1024 * 1024;

  final Uri _referenceBaseUri;
  final String _referenceTransportToken;
  final ControlPlaneTransport _referenceTransport;

  @override
  Future<core.GovernedPromptSubmission> submitPrompt(
    String objective,
    core.DesktopUserSession session,
  ) async {
    final normalized = objective.trim();
    if (normalized.isEmpty) {
      throw const core.IdentityClientException('Prompt must not be empty');
    }
    if (normalized.length > 20000) {
      throw const core.IdentityClientException(
        'Prompt exceeds the Desktop input limit',
      );
    }

    final references = ReferenceAssetSubmissionBus.pending;
    if (references.isNotEmpty && !_isReferenceCapableObjective(normalized)) {
      throw const core.IdentityClientException(
        'Reference images may only be submitted through Web Factory or Video Factory',
      );
    }
    _validateReferenceAssets(references);

    final referenceAssetIds = <String>[];
    for (final reference in references) {
      referenceAssetIds.add(await _uploadReferenceAsset(reference, session));
    }

    final payload = await _sessionPost(
      '/v1/desktop/intent',
      <String, Object?>{
        'objective': normalized,
        'reference_asset_ids': referenceAssetIds,
      },
      'authenticated intent',
      session,
      expectedStatus: HttpStatus.created,
    );
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
      throw const core.IdentityClientException(
        'Authenticated intent response is malformed',
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

  Future<String> _uploadReferenceAsset(
    ReferenceAssetDraft reference,
    core.DesktopUserSession session,
  ) async {
    final payload = await _sessionPost(
      '/v1/reference-assets',
      <String, Object?>{
        'filename': reference.filename,
        'mime_type': reference.mimeType,
        'role': reference.role.wireValue,
        'instruction': reference.instruction,
        'sha256': reference.sha256Hex,
        'content_base64': base64Encode(reference.bytes),
      },
      'reference image upload',
      session,
      expectedStatus: HttpStatus.created,
    );
    final assetId = payload['asset_id'];
    final digest = payload['sha256'];
    final sizeBytes = payload['size_bytes'];
    if (assetId is! String ||
        !assetId.startsWith('ref-') ||
        digest != reference.sha256Hex ||
        sizeBytes != reference.sizeBytes) {
      throw const core.IdentityClientException(
        'Reference image upload response is malformed',
      );
    }
    return assetId;
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
        throw const FormatException('response is not a JSON object');
      }
      payload = decoded;
    } on FormatException catch (error) {
      throw core.IdentityClientException(
        'Desktop $label response is malformed: ${error.message}',
      );
    }
    if (response.statusCode == HttpStatus.unauthorized ||
        response.statusCode == HttpStatus.forbidden) {
      throw const core.IdentityClientException(
        'Desktop session is invalid or expired',
      );
    }
    if (response.statusCode != expectedStatus) {
      final error = payload['error'];
      throw core.IdentityClientException(
        error is String && error.isNotEmpty ? error : 'Desktop $label failed',
      );
    }
    return payload;
  }

  static void _validateReferenceAssets(List<ReferenceAssetDraft> references) {
    if (references.length > _maxReferenceAssets) {
      throw const core.IdentityClientException(
        'A request can use at most 20 reference images',
      );
    }
    var totalBytes = 0;
    final digests = <String>{};
    for (final reference in references) {
      if (reference.filename.trim().isEmpty || reference.filename.length > 180) {
        throw const core.IdentityClientException(
          'Reference image filename is invalid',
        );
      }
      if (!const <String>{'image/jpeg', 'image/png', 'image/webp'}
          .contains(reference.mimeType)) {
        throw const core.IdentityClientException(
          'Reference image type is unsupported',
        );
      }
      if (reference.sizeBytes <= 0 ||
          reference.sizeBytes > _maxReferenceAssetBytes) {
        throw const core.IdentityClientException(
          'Reference image exceeds the per-image size limit',
        );
      }
      if (reference.sha256Hex.length != 64 ||
          !RegExp(r'^[0-9a-f]{64}$').hasMatch(reference.sha256Hex)) {
        throw const core.IdentityClientException(
          'Reference image digest is invalid',
        );
      }
      if (!digests.add(reference.sha256Hex)) {
        throw const core.IdentityClientException(
          'Duplicate reference image content is not allowed',
        );
      }
      totalBytes += reference.sizeBytes;
    }
    if (totalBytes > _maxReferenceTotalBytes) {
      throw const core.IdentityClientException(
        'Reference images exceed the 100 MiB request limit',
      );
    }
  }
}

bool _isReferenceCapableObjective(String objective) {
  final normalized = objective.trimLeft().toLowerCase();
  if (normalized.startsWith('video creation task:') ||
      normalized.startsWith('video oluşturma görevi:')) {
    return true;
  }
  const webTerms = <String>{
    'website',
    'web site',
    'web sitesi',
    'landing page',
    'internet sitesi',
  };
  return webTerms.any(normalized.contains);
}
