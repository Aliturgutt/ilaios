import 'approvals_view.dart';
import 'evidence_view.dart';

export 'operational_views_legacy.dart' hide EvidenceView, GovernanceView;

/// Compatibility entry point used by the canonical Desktop shell.
///
/// The shell historically routes the Approvals navigation item through
/// `GovernanceView`. Keep that public contract stable while rendering the
/// approved dark/light Approvals design and preserving the authoritative
/// governance decision callback.
class GovernanceView extends ApprovalsView {
  const GovernanceView({
    required super.snapshot,
    required super.status,
    super.approverId,
    super.onDecision,
    super.key,
  });
}

/// Compatibility entry point for the canonical Evidence navigation item.
///
/// The screenshot references define presentation only. Evidence records remain
/// authority-derived from the operational snapshot, and unsupported fields are
/// rendered as unavailable rather than synthesized.
class EvidenceView extends ReferenceEvidenceView {
  const EvidenceView({
    required super.snapshot,
    required super.status,
    super.onSaveArtifact,
    super.key,
  });
}
