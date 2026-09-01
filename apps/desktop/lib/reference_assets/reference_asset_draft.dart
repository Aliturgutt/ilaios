import 'dart:typed_data';

enum ReferenceAssetRoleDraft {
  style,
  subject,
  product,
  environment,
  logo,
  storyboard,
  firstFrame,
  lastFrame,
  other,
}

extension ReferenceAssetRoleWire on ReferenceAssetRoleDraft {
  String get wireValue => switch (this) {
        ReferenceAssetRoleDraft.firstFrame => 'first_frame',
        ReferenceAssetRoleDraft.lastFrame => 'last_frame',
        _ => name,
      };

  String get label => switch (this) {
        ReferenceAssetRoleDraft.style => 'Style',
        ReferenceAssetRoleDraft.subject => 'Subject',
        ReferenceAssetRoleDraft.product => 'Product',
        ReferenceAssetRoleDraft.environment => 'Environment',
        ReferenceAssetRoleDraft.logo => 'Logo',
        ReferenceAssetRoleDraft.storyboard => 'Storyboard',
        ReferenceAssetRoleDraft.firstFrame => 'First frame',
        ReferenceAssetRoleDraft.lastFrame => 'Last frame',
        ReferenceAssetRoleDraft.other => 'Other',
      };
}

class ReferenceAssetDraft {
  const ReferenceAssetDraft({
    required this.filename,
    required this.mimeType,
    required this.bytes,
    required this.sha256Hex,
    this.role = ReferenceAssetRoleDraft.style,
    this.instruction,
  });

  final String filename;
  final String mimeType;
  final Uint8List bytes;
  final String sha256Hex;
  final ReferenceAssetRoleDraft role;
  final String? instruction;

  int get sizeBytes => bytes.length;

  ReferenceAssetDraft copyWith({
    ReferenceAssetRoleDraft? role,
    String? instruction,
    bool clearInstruction = false,
  }) =>
      ReferenceAssetDraft(
        filename: filename,
        mimeType: mimeType,
        bytes: bytes,
        sha256Hex: sha256Hex,
        role: role ?? this.role,
        instruction: clearInstruction ? null : (instruction ?? this.instruction),
      );
}

/// In-process handoff between the visible reference dock and the authenticated
/// IdentityClient. It never writes file paths or image bytes to prompts.
class ReferenceAssetSubmissionBus {
  ReferenceAssetSubmissionBus._();

  static List<ReferenceAssetDraft> _pending = const <ReferenceAssetDraft>[];

  static List<ReferenceAssetDraft> get pending =>
      List<ReferenceAssetDraft>.unmodifiable(_pending);

  static void replace(Iterable<ReferenceAssetDraft> assets) {
    _pending = List<ReferenceAssetDraft>.unmodifiable(assets);
  }

  static void clear() {
    _pending = const <ReferenceAssetDraft>[];
  }
}
