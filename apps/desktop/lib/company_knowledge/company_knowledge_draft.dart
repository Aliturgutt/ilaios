import 'dart:typed_data';

/// Local-only PDF/DOCX bytes awaiting authenticated company-Knowledge upload.
///
/// File paths are intentionally not retained. The authenticated Desktop client
/// uploads these bytes to the existing tenant-bound `/v1/company-knowledge`
/// boundary; document content is never appended to the free-form prompt.
class CompanyKnowledgeDraft {
  const CompanyKnowledgeDraft({
    required this.filename,
    required this.mimeType,
    required this.bytes,
    required this.sha256Hex,
  });

  final String filename;
  final String mimeType;
  final Uint8List bytes;
  final String sha256Hex;

  int get sizeBytes => bytes.length;
}

class CompanyKnowledgeSubmissionBus {
  CompanyKnowledgeSubmissionBus._();

  static List<CompanyKnowledgeDraft> _pending = const <CompanyKnowledgeDraft>[];

  static List<CompanyKnowledgeDraft> get pending =>
      List<CompanyKnowledgeDraft>.unmodifiable(_pending);

  static void replace(List<CompanyKnowledgeDraft> documents) {
    _pending = List<CompanyKnowledgeDraft>.unmodifiable(documents);
  }

  static void clear() {
    _pending = const <CompanyKnowledgeDraft>[];
  }
}
