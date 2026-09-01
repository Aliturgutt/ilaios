export 'identity_client_core.dart' hide IdentityClient;

import 'dart:convert';
import 'dart:io';

import '../business_context/business_capability_context.dart';
import '../control_plane/client.dart';
import '../reference_assets/reference_asset_draft.dart';
import '../source_media/source_media_draft.dart';
import 'identity_client_core.dart' as core;

/// Backward-compatible IdentityClient that extends the existing authenticated
/// session client with governed Web/Video reference assets, one private source-
/// video input, and optional bounded business-capability metadata. Raw media
/// bytes are uploaded separately; execution intent receives only immutable
/// server-side asset identifiers plus the optional context code. The free-form
/// objective remains unchanged.
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
      assetBaseUri: baseUri,
      assetTransportToken: transportToken,
    );
  }

  IdentityClient._({
    required super.baseUri,
    required super.transportToken,
    required ControlPlaneTransport transport,
    super.retryDelay,
    required this._assetBaseUri,
    required this._assetTransportToken,
  })  : _assetTransport = transport,
        super(transport: transport);

  static const int _maxReferenceAssets = 20;
  static const int _maxReferenceAssetBytes = 10 * 1024 * 1024;
  static const int _maxReferenceTotalBytes = 100 * 1024 * 1024;
  static const int _maxSourceMediaBytes = 128 * 1024 * 1024;

  final Uri _assetBaseUri;
  final String _assetTransportToken;
  final ControlPlaneTransport _assetTransport;

  @override
  Future<core.GovernedPromptSubmission> submitPrompt(
    String objective,
    core.DesktopUserSession session, {
    BusinessCapabilityContext? businessContext,
  }) async {
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
    final source = SourceMediaSubmissionBus.pending;
    if (references.isNotEmpty) {
      final factoryCount = _referenceFactoryCount(normalized);
      if (factoryCount == 0) {
        throw const core.IdentityClientException(
          'Reference images may only be submitted through Web Factory or Video Factory',
        );
      }
      if (factoryCount != 1) {
        throw const core.IdentityClientException(
          'A reference-image request must target exactly one of Web Factory or Video Factory',
        );
      }
    }
    if (source != null && !_isVideoFactoryObjective(normalized)) {
      throw const core.IdentityClientException(
        'Source video may only be submitted through Video Factory',
      );
    }
    if (source != null && references.isNotEmpty) {
      throw const core.IdentityClientException(
        'Source video and reference images cannot be combined until that exact revision contract is verified',
      );
    }
    _validateReferenceAssets(references);
    if (source != null) _validateSourceMedia(source);

    final referenceAssetIds = <String>[];
    String? sourceAssetId;
    try {
      for (final reference in references) {
        referenceAssetIds.add(await _uploadReferenceAsset(reference, session));
      }
      if (source != null) {
        sourceAssetId = await _uploadSourceMedia(source, session);
      }

      final payload = await _sessionPost(
        '/v1/desktop/intent',
        <String, Object?>{
          'objective': normalized,
          'reference_asset_ids': referenceAssetIds,
          'source_media_asset_id': ?sourceAssetId,
          'business_context_code': businessContext?.contextCode,
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
      final returnedBusinessContextCode = payload['business_context_code'];
      if (businessContext != null &&
          returnedBusinessContextCode != businessContext.contextCode) {
        throw const core.IdentityClientException(
          'Authenticated intent business context is malformed',
        );
      }
      return core.GovernedPromptSubmission(
        goalId: goalId,
        jobId: jobId,
        state: state,
        requestId: requestId,
        executionStatus: executionStatus,
      );
    } catch (_) {
      if (sourceAssetId != null) {
        try {
          await _discardSourceMedia(sourceAssetId, session);
        } catch (_) {
          // The source may already be immutably bound to a prepared request.
          // Server-side retention/recovery remains authoritative in that case.
        }
      }
      rethrow;
    }
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

  Future<String> _uploadSourceMedia(
    SourceMediaDraft source,
    core.DesktopUserSession session,
  ) async {
    final payload = await _sessionPost(
      '/v1/source-media',
      <String, Object?>{
        'filename': source.filename,
        'mime_type': source.mimeType,
        'sha256': source.sha256Hex,
        'content_base64': base64Encode(source.bytes),
      },
      'source video upload',
      session,
      expectedStatus: HttpStatus.created,
    );
    final assetId = payload['asset_id'];
    final digest = payload['sha256'];
    final sizeBytes = payload['size_bytes'];
    if (assetId is! String ||
        !assetId.startsWith('src-') ||
        digest != source.sha256Hex ||
        sizeBytes != source.sizeBytes) {
      throw const core.IdentityClientException(
        'Source video upload response is malformed',
      );
    }
    return assetId;
  }

  Future<void> _discardSourceMedia(
    String assetId,
    core.DesktopUserSession session,
  ) async {
    await _sessionPost(
      '/v1/source-media/discard',
      <String, Object?>{'asset_id': assetId},
      'source video discard',
      session,
      expectedStatus: HttpStatus.ok,
    );
  }

  Future<Map<String, dynamic>> _sessionPost(
    String path,
    Map<String, Object?> body,
    String label,
    core.DesktopUserSession session, {
    required int expectedStatus,
  }) async {
    final response = await _assetTransport.post(
      _assetBaseUri.resolve(path),
      body: jsonEncode(body),
      headers: <String, String>{
        'Authorization': 'Bearer $_assetTransportToken',
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
      if (reference.instruction != null &&
          reference.instruction!.trim().length > 500) {
        throw const core.IdentityClientException(
          'Reference image instruction exceeds 500 characters',
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

  static void _validateSourceMedia(SourceMediaDraft source) {
    if (source.filename.trim().isEmpty ||
        source.filename.length > 180 ||
        !source.filename.toLowerCase().endsWith('.mp4')) {
      throw const core.IdentityClientException('Source video filename is invalid');
    }
    if (source.sizeBytes < 12 || source.sizeBytes > _maxSourceMediaBytes) {
      throw const core.IdentityClientException(
        'Source video is empty or exceeds the 128 MiB limit',
      );
    }
    if (source.bytes[4] != 0x66 ||
        source.bytes[5] != 0x74 ||
        source.bytes[6] != 0x79 ||
        source.bytes[7] != 0x70) {
      throw const core.IdentityClientException(
        'Source video does not contain an MP4 signature',
      );
    }
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(source.sha256Hex)) {
      throw const core.IdentityClientException('Source video digest is invalid');
    }
  }
}

bool _isVideoFactoryObjective(String objective) {
  final normalized = objective.trimLeft().toLowerCase();
  return normalized.startsWith('video creation task:') ||
      normalized.startsWith('video oluşturma görevi:');
}

int _referenceFactoryCount(String objective) {
  final normalized = objective.trimLeft().toLowerCase();
  final video = _isVideoFactoryObjective(normalized);
  const webTerms = <String>{
    'website',
    'web site',
    'web sitesi',
    'landing page',
    'internet sitesi',
    'web app',
    'web application',
    'web uygulaması',
    'web uygulamasi',
    'dashboard',
    'admin panel',
    'management dashboard',
    'yönetim paneli',
    'yonetim paneli',
  };
  final web = webTerms.any(normalized.contains);
  return (video ? 1 : 0) + (web ? 1 : 0);
}
