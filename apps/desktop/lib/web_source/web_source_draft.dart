import 'dart:typed_data';

/// Local-only existing Web source archive awaiting authenticated admission.
///
/// The source path is intentionally not retained and archive bytes are never
/// inserted into prompt text. IdentityClient uploads this ZIP separately and
/// execution intent carries only the immutable server-side `wsrc-*` asset ID.
class WebSourceDraft {
  const WebSourceDraft({
    required this.filename,
    required this.bytes,
    required this.sha256Hex,
  });

  final String filename;
  final Uint8List bytes;
  final String sha256Hex;

  int get sizeBytes => bytes.length;
}

class WebSourceSubmissionBus {
  WebSourceSubmissionBus._();

  static WebSourceDraft? _pending;

  static WebSourceDraft? get pending => _pending;

  static void replace(WebSourceDraft source) {
    _pending = source;
  }

  static void clear() {
    _pending = null;
  }
}
