import 'approvals_view.dart';

export 'operational_views_legacy.dart' hide GovernanceView;

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
