import 'dart:typed_data';

/// Local-only source-video bytes awaiting authenticated upload.
///
/// The file path is intentionally not retained and bytes are never projected into
/// the prompt. The authenticated IdentityClient uploads this object separately and
/// sends only the immutable server-side `src-*` identifier in the intent payload.
class SourceMediaDraft {
  const SourceMediaDraft({
    required this.filename,
    required this.bytes,
    required this.sha256Hex,
  });

  final String filename;
  final Uint8List bytes;
  final String sha256Hex;

  String get mimeType => 'video/mp4';
  int get sizeBytes => bytes.length;
}

class SourceMediaSubmissionBus {
  SourceMediaSubmissionBus._();

  static SourceMediaDraft? _pending;

  static SourceMediaDraft? get pending => _pending;

  static void replace(SourceMediaDraft source) {
    _pending = source;
  }

  static void clear() {
    _pending = null;
  }
}
