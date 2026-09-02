import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import '../control_plane/client.dart';
import '../identity/identity_client.dart';

const int maxCompanyKnowledgeBytes = 25 * 1024 * 1024;
const Set<String> supportedCompanyKnowledgeMimeTypes = <String>{
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
};

class CompanyKnowledgeUploadResult {
  const CompanyKnowledgeUploadResult({
    required this.sourceId,
    required this.latestVersion,
    required this.state,
    required this.filename,
    required this.mimeType,
    required this.sha256Hex,
  });

  final String sourceId;
  final int latestVersion;
  final String state;
  final String filename;
  final String mimeType;
  final String sha256Hex;
}

class CompanyKnowledgeClient {
  CompanyKnowledgeClient({
    required Uri baseUri,
    required String transportToken,
    ControlPlaneTransport? transport,
  })  : _baseUri = baseUri,
        _transportToken = transportToken,
        _transport = transport ?? const IoControlPlaneTransport();

  final Uri _baseUri;
  final String _transportToken;
  final ControlPlaneTransport _transport;

  Future<CompanyKnowledgeUploadResult> uploadFile(
    File file,
    DesktopUserSession session,
  ) async {
    final stat = await file.stat();
    if (stat.type != FileSystemEntityType.file ||
        stat.size <= 0 ||
        stat.size > maxCompanyKnowledgeBytes) {
      throw const IdentityClientException(
        'Company document is empty or exceeds the 25 MiB limit',
      );
    }
    final filename = _basename(file.path);
    if (filename.isEmpty || filename.length > 180) {
      throw const IdentityClientException('Company document filename is invalid');
    }
    final mimeType = _mimeType(filename);
    if (!supportedCompanyKnowledgeMimeTypes.contains(mimeType)) {
      throw const IdentityClientException(
        'Company document must be PDF or DOCX',
      );
    }
    final bytes = await file.readAsBytes();
    if (bytes.length != stat.size) {
      throw const IdentityClientException(
        'Company document changed while it was being read',
      );
    }
    final digest = sha256.convert(bytes).toString();
    final response = await _transport.post(
      _baseUri.resolve('/v1/company-knowledge'),
      body: jsonEncode(<String, Object?>{
        'filename': filename,
        'mime_type': mimeType,
        'sha256': digest,
        'content_base64': base64Encode(bytes),
      }),
      headers: <String, String>{
        'Authorization': 'Bearer $_transportToken',
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
      throw IdentityClientException(
        'Desktop company document response is malformed: ${error.message}',
      );
    }
    if (response.statusCode == HttpStatus.unauthorized ||
        response.statusCode == HttpStatus.forbidden) {
      throw const IdentityClientException('Desktop session is invalid or expired');
    }
    if (response.statusCode != HttpStatus.created) {
      final error = payload['error'];
      throw IdentityClientException(
        error is String && error.isNotEmpty
            ? error
            : 'Desktop company document upload failed',
      );
    }

    final sourceId = payload['source_id'];
    final latestVersion = payload['latest_version'];
    final state = payload['state'];
    final returnedFilename = payload['filename'];
    final returnedMimeType = payload['mime_type'];
    final returnedDigest = payload['sha256'];
    final knowledgeScope = payload['knowledge_scope'];
    if (sourceId is! String ||
        !sourceId.startsWith('company-file-') ||
        latestVersion is! int ||
        latestVersion <= 0 ||
        state is! String ||
        state.isEmpty ||
        returnedFilename != filename ||
        returnedMimeType != mimeType ||
        returnedDigest != digest ||
        knowledgeScope != 'company') {
      throw const IdentityClientException(
        'Desktop company document upload response is malformed',
      );
    }
    return CompanyKnowledgeUploadResult(
      sourceId: sourceId,
      latestVersion: latestVersion,
      state: state,
      filename: filename,
      mimeType: mimeType,
      sha256Hex: digest,
    );
  }
}

String _mimeType(String filename) {
  final normalized = filename.toLowerCase();
  if (normalized.endsWith('.pdf')) return 'application/pdf';
  if (normalized.endsWith('.docx')) {
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  }
  return '';
}

String _basename(String path) {
  final normalized = path.replaceAll('\\', '/');
  final parts = normalized.split('/').where((part) => part.isNotEmpty).toList();
  return parts.isEmpty ? path : parts.last;
}
