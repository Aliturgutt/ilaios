import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/operational_snapshot.dart';
import 'approvals_view.dart';
import 'evidence_view.dart';

export 'operational_views_legacy.dart' hide EvidenceView, GovernanceView;

/// Compatibility entry point used by the canonical Desktop shell.
///
/// The shell historically routes the Approvals navigation item through
/// `GovernanceView`. Keep that public contract stable while rendering the
/// approved dark/light Approvals design and preserving the authoritative
/// governance decision callback.
class GovernanceView extends StatelessWidget {
  const GovernanceView({
    required this.snapshot,
    required this.status,
    this.approverId,
    this.onDecision,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final String? approverId;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onDecision;

  bool get _hasQueueItems {
    final raw = snapshot.governanceState['work'];
    return raw is List<Object?> && raw.isNotEmpty;
  }

  bool get _governanceUnavailable => snapshot.governanceState.isEmpty;

  @override
  Widget build(BuildContext context) {
    if (_hasQueueItems) {
      return ApprovalsView(
        snapshot: snapshot,
        status: status,
        approverId: approverId,
        onDecision: onDecision,
      );
    }

    final turkish = Localizations.localeOf(context).languageCode == 'tr';
    return Container(
      key: const Key('reference-approvals-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(24, 18, 24, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            turkish ? 'Onaylar' : 'Approvals',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  height: 1.15,
                ),
          ),
          const SizedBox(height: 18),
          Expanded(
            child: Container(
              key: const Key('approvals-table'),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLowest,
                border: Border.all(
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              alignment: Alignment.center,
              child: Text(
                _governanceUnavailable
                    ? (turkish
                        ? 'Yönetişim verisi şu anda kullanılamıyor.'
                        : 'Governance data is currently unavailable.')
                    : (turkish
                        ? 'Karar kuyruğunda talep yok.'
                        : 'No requests in the decision queue.'),
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
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
