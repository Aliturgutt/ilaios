import 'dart:convert';
import 'dart:io';

import '../control_plane/client.dart';
import '../reference_assets/reference_asset_draft.dart';

typedef IdentityRetryDelay = Future<void> Function(Duration duration);

class IdentityProviderOption {
  const IdentityProviderOption({
    required this.providerId,
    required this.displayName,
  });

  final String providerId;
  final String displayName;
}

class IdentityAuthStart {
  const IdentityAuthStart({
    required this.providerId,
    required this.state,
    required this.authorizationUri,
  });

  final String providerId;
  final String state;
  final Uri authorizationUri;
}

class DesktopUserSession {
  const DesktopUserSession({
    required this.sessionId,
    required this.providerId,
    required this.principalId,
    required this.tenantId,
    this.displayIdentity,
  });

  final String sessionId;
  final String providerId;
  final String principalId;
  final String tenantId;
  final String? displayIdentity;
}

class GovernedPromptSubmission extends PromptSubmission {
  const GovernedPromptSubmission({
    required super.goalId,
    required super.jobId,
    required super.state,
    required this.requestId,
    required this.executionStatus,
  });

  final String requestId;
  final String executionStatus;
}

class IdentityClientException implements Exception {
  const IdentityClientException(this.message);
  final String message;

  @override
  String toString() => 'IdentityClientException: $message';
}

class IdentityClient {
  IdentityClient({
    required Uri baseUri,
    required String transportToken,
    ControlPlaneTransport? transport,
    IdentityRetryDelay? retryDelay,
  })  : _baseUri = _validatedBaseUri(baseUri),
        _transportToken = _validatedToken(transportToken),
        _transport = transport ?? const IoControlPlaneTransport(),
        _retryDelay = retryDelay ?? _defaultRetryDelay;

  static const Duration _startupRetryDelay = Duration(milliseconds: 350);
  static const int _maxReferenceAssets = 20;
  static const int _maxReferenceAssetBytes = 10 * 1024 * 1024;
  static const int _maxReferenceTotalBytes = 100 * 1024 * 1024;

  final Uri _baseUri;
  final String _transportToken;
  final ControlPlaneTransport _transport;
  final IdentityRetryDelay _retryDelay;

  Future<List<IdentityProviderOption>> fetchProviders() async {
    final payload = await _get('/v1/auth/providers', 'identity providers');
    final raw = payload['providers'];
    if (raw is! List<Object?>) {
      throw const IdentityClientException('Identity providers response is malformed');
    }
    final providers = <IdentityProviderOption>[];
    for (final item in raw) {
      if (item is! Map<String, dynamic>) {
        throw const IdentityClientException(
          'Identity providers response is malformed',
        );
      }
      final providerId = item['provider_id'];
      final displayName = item['display_name'];
      if (providerId is! String ||
          providerId.isEmpty ||
          displayName is! String ||
          displayName.isEmpty) {
        throw const IdentityClientException(
          'Identity providers response is malformed',
        );
      }
      providers.add(
        IdentityProviderOption(
          providerId: providerId,
          displayName: displayName,
        ),
      );
    }
    return List<IdentityProviderOption>.unmodifiable(providers);
  }

  Future<IdentityAuthStart> start(String providerId) async {
    final normalized = providerId.trim();
    if (normalized.isEmpty) {
      throw const IdentityClientException('Identity provider is required');
    }
    final payload = await _post(
      '/v1/auth/start',
      <String, Object?>{'provider_id': normalized},
      'sign-in start',
      expectedStatus: HttpStatus.created,
      retryTransportAuthentication: true,
    );
    final state = payload['state'];
    final authorizationUrl = payload['authorization_url'];
    final returnedProvider = payload['provider_id'];
    if (state is! String ||
        state.isEmpty ||
        authorizationUrl is! String ||
        returnedProvider != normalized) {
      throw const IdentityClientException('Sign-in start response is malformed');
    }
    final uri = Uri.tryParse(authorizationUrl);
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
      throw const IdentityClientException(
        'Identity provider returned an unsafe authorization URL',
      );
    }
    return IdentityAuthStart(
      providerId: normalized,
      state: state,
      authorizationUri: uri,
    );
  }

  Future<DesktopUserSession?> poll(String state) async {
    final normalized = state.trim();
    if (normalized.isEmpty) {
      throw const IdentityClientException('Sign-in state is required');
    }
    final path = Uri(
      path: '/v1/auth/status',
      queryParameters: <String, String>{'state': normalized},
    ).toString();
    final payload = await _get(path, 'sign-in status');
    final status = payload['status'];
    if (status == 'pending') return null;
    if (status is String && status.startsWith('rejected:')) {
      throw IdentityClientException(status.substring('rejected:'.length));
    }
    if (status != 'authenticated') {
      throw const IdentityClientException('Sign-in status is malformed');
    }
    final sessionId = payload['session_id'];
    final providerId = payload['provider_id'];
    final principalId = payload['principal_id'];
    final tenantId = payload['tenant_id'];
    final displayIdentity = payload['display_identity'];
    if (sessionId is! String ||
        sessionId.isEmpty ||
        providerId is! String ||
        providerId.isEmpty ||
        principalId is! String ||
        principalId.isEmpty ||
        tenantId is! String ||
        tenantId.isEmpty ||
        (displayIdentity != null && displayIdentity is! String)) {
      throw const IdentityClientException('Authenticated session is malformed');
    }
    return DesktopUserSession(
      sessionId: sessionId,
      providerId: providerId,
      principalId: principalId,
      tenantId: tenantId,
      displayIdentity: displayIdentity as String?,
    );
  }

  Future<GovernedPromptSubmission> submitPrompt(
    String objective,
    DesktopUserSession session,
  ) async {
    final normalized = objective.trim();
    if (normalized.isEmpty) {
      throw const IdentityClientException('Prompt must not be empty');
    }
    if (normalized.length > 20000) {
      throw const IdentityClientException('Prompt exceeds the Desktop input limit');
    }

    final references = ReferenceAssetSubmissionBus.pending;
    if (references.isNotEmpty && !_isVideoObjective(normalized)) {
      throw const IdentityClientException(
        'Reference images may only be submitted through Video Factory',
      );
    }
    _validateReferenceAssets(references);
    final referenceAssetIds = <String>[];
    for (final reference in references) {
      referenceAssetIds.add(
        await _uploadReferenceAsset(reference, session),
      );
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
      throw const IdentityClientException(
        'Authenticated intent response is malformed',
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

  Future<String> _uploadReferenceAsset(
    ReferenceAssetDraft reference,
    DesktopUserSession session,
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
      throw const IdentityClientException(
        'Reference image upload response is malformed',
      );
    }
    return assetId;
  }

  Future<String> decideExecution(
    String requestId,
    GovernanceDecision decision,
    DesktopUserSession session,
  ) async {
    final normalized = requestId.trim();
    if (normalized.isEmpty) {
      throw const IdentityClientException('Execution request is required');
    }
    final expectedStatus = decision == GovernanceDecision.approved
        ? HttpStatus.accepted
        : HttpStatus.ok;
    final payload = await _sessionPost(
      '/v1/execution/decision',
      <String, Object?>{
        'request_id': normalized,
        'decision': decision.name,
      },
      'execution decision',
      session,
      expectedStatus: expectedStatus,
    );
    if (payload['request_id'] != normalized) {
      throw const IdentityClientException('Execution decision response is malformed');
    }
    final status = payload['execution_status'];
    if (status is! String ||
        (status != 'EXECUTION_STARTED' && status != 'DENIED')) {
      throw const IdentityClientException('Execution decision response is malformed');
    }
    return status;
  }

  Future<void> resumeExecution(
    String requestId,
    DesktopUserSession session,
  ) async {
    final normalized = requestId.trim();
    if (normalized.isEmpty) {
      throw const IdentityClientException('Execution request is required');
    }
    final payload = await _sessionPost(
      '/v1/execution/resume',
      <String, Object?>{'request_id': normalized},
      'execution resume',
      session,
      expectedStatus: HttpStatus.accepted,
    );
    if (payload['request_id'] != normalized ||
        payload['execution_status'] != 'RESUME_REQUESTED') {
      throw const IdentityClientException('Execution resume response is malformed');
    }
  }

  Future<String> fetchExecutionStatus(
    String requestId,
    DesktopUserSession session,
  ) async {
    final normalized = requestId.trim();
    if (normalized.isEmpty) {
      throw const IdentityClientException('Execution request is required');
    }
    final path = Uri(
      path: '/v1/execution/status',
      queryParameters: <String, String>{'request_id': normalized},
    ).toString();
    final payload = await _sessionGet(path, 'execution status', session);
    if (payload['request_id'] != normalized) {
      throw const IdentityClientException('Execution status response is malformed');
    }
    final status = payload['execution_status'];
    if (status is! String || status.isEmpty) {
      throw const IdentityClientException('Execution status response is malformed');
    }
    return status;
  }

  Future<void> logout(DesktopUserSession session) async {
    await _post(
      '/v1/auth/logout',
      <String, Object?>{'session_id': session.sessionId},
      'logout',
      expectedStatus: HttpStatus.ok,
    );
  }

  Future<Map<String, dynamic>> _get(String path, String label) async {
    final uri = _baseUri.resolve(path);
    final headers = <String, String>{'Authorization': 'Bearer $_transportToken'};
    var response = await _transport.get(uri, headers: headers);
    if (_isTransportAuthenticationFailure(response)) {
      await _retryDelay(_startupRetryDelay);
      response = await _transport.get(uri, headers: headers);
    }
    final payload = _decode(response, label);
    if (_isTransportAuthenticationFailure(response)) {
      throw const IdentityClientException(
        'Desktop identity transport authentication failed',
      );
    }
    if (response.statusCode != HttpStatus.ok) {
      throw IdentityClientException('Desktop $label query failed');
    }
    return payload;
  }

  Future<Map<String, dynamic>> _sessionGet(
    String path,
    String label,
    DesktopUserSession session,
  ) async {
    final response = await _transport.get(
      _baseUri.resolve(path),
      headers: <String, String>{
        'Authorization': 'Bearer $_transportToken',
        'X-ILAIOS-Session': session.sessionId,
      },
    );
    return _checkedPayload(response, label, HttpStatus.ok);
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, Object?> body,
    String label, {
    required int expectedStatus,
    bool retryTransportAuthentication = false,
  }) async {
    final uri = _baseUri.resolve(path);
    final encodedBody = jsonEncode(body);
    final headers = <String, String>{'Authorization': 'Bearer $_transportToken'};
    var response = await _transport.post(
      uri,
      body: encodedBody,
      headers: headers,
    );
    if (retryTransportAuthentication &&
        _isTransportAuthenticationFailure(response)) {
      await _retryDelay(_startupRetryDelay);
      response = await _transport.post(
        uri,
        body: encodedBody,
        headers: headers,
      );
    }
    if (retryTransportAuthentication &&
        _isTransportAuthenticationFailure(response)) {
      _decode(response, label);
      throw const IdentityClientException(
        'Desktop identity transport authentication failed',
      );
    }
    return _checkedPayload(response, label, expectedStatus);
  }

  Future<Map<String, dynamic>> _sessionPost(
    String path,
    Map<String, Object?> body,
    String label,
    DesktopUserSession session, {
    required int expectedStatus,
  }) async {
    final response = await _transport.post(
      _baseUri.resolve(path),
      body: jsonEncode(body),
      headers: <String, String>{
        'Authorization': 'Bearer $_transportToken',
        'X-ILAIOS-Session': session.sessionId,
      },
    );
    return _checkedPayload(response, label, expectedStatus);
  }

  Map<String, dynamic> _checkedPayload(
    ControlPlaneResponse response,
    String label,
    int expectedStatus,
  ) {
    final payload = _decode(response, label);
    if (response.statusCode == HttpStatus.unauthorized ||
        response.statusCode == HttpStatus.forbidden) {
      throw const IdentityClientException('Desktop session is invalid or expired');
    }
    if (response.statusCode != expectedStatus) {
      final error = payload['error'];
      throw IdentityClientException(
        error is String && error.isNotEmpty ? error : 'Desktop $label failed',
      );
    }
    return payload;
  }

  static void _validateReferenceAssets(List<ReferenceAssetDraft> references) {
    if (references.length > _maxReferenceAssets) {
      throw const IdentityClientException(
        'A video can use at most 20 reference images',
      );
    }
    var totalBytes = 0;
    final digests = <String>{};
    for (final reference in references) {
      if (reference.filename.trim().isEmpty || reference.filename.length > 180) {
        throw const IdentityClientException('Reference image filename is invalid');
      }
      if (!const <String>{'image/jpeg', 'image/png', 'image/webp'}
          .contains(reference.mimeType)) {
        throw const IdentityClientException('Reference image type is unsupported');
      }
      if (reference.sizeBytes <= 0 ||
          reference.sizeBytes > _maxReferenceAssetBytes) {
        throw const IdentityClientException(
          'A reference image exceeds the 10 MiB limit',
        );
      }
      if (reference.instruction != null &&
          reference.instruction!.trim().length > 500) {
        throw const IdentityClientException(
          'Reference image instruction exceeds 500 characters',
        );
      }
      if (!digests.add(reference.sha256Hex)) {
        throw const IdentityClientException(
          'Duplicate reference images are not allowed',
        );
      }
      totalBytes += reference.sizeBytes;
    }
    if (totalBytes > _maxReferenceTotalBytes) {
      throw const IdentityClientException(
        'Reference images exceed the 100 MiB request limit',
      );
    }
  }

  static bool _isVideoObjective(String objective) {
    final normalized = objective.trimLeft().toLowerCase();
    return normalized.startsWith('video creation task:') ||
        normalized.startsWith('video oluşturma görevi:');
  }

  static bool _isTransportAuthenticationFailure(
    ControlPlaneResponse response,
  ) =>
      response.statusCode == HttpStatus.unauthorized ||
      response.statusCode == HttpStatus.forbidden;

  static Future<void> _defaultRetryDelay(Duration duration) =>
      Future<void>.delayed(duration);

  static Map<String, dynamic> _decode(
    ControlPlaneResponse response,
    String label,
  ) {
    try {
      final value = jsonDecode(response.body);
      if (value is Map<String, dynamic>) return value;
    } on FormatException {
      // Stabilized below.
    }
    throw IdentityClientException('Desktop returned malformed $label JSON');
  }

  static Uri _validatedBaseUri(Uri uri) {
    final loopbackHost =
        uri.host == '127.0.0.1' || uri.host == '::1' || uri.host == 'localhost';
    if (uri.scheme != 'http' || !loopbackHost || !uri.hasPort) {
      throw ArgumentError.value(
        uri,
        'baseUri',
        'must be an explicit loopback HTTP endpoint',
      );
    }
    return uri;
  }

  static String _validatedToken(String token) {
    if (token.trim().isEmpty) {
      throw ArgumentError.value(token, 'transportToken', 'must not be empty');
    }
    return token;
  }
}
