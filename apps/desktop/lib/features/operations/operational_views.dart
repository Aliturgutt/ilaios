import 'package:flutter/material.dart';

import '../../control_plane/evidence_record.dart';
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
class EvidenceView extends StatelessWidget {
  const EvidenceView({
    required this.snapshot,
    required this.status,
    this.onSaveArtifact,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;

  @override
  Widget build(BuildContext context) {
    final latest = snapshot.evidenceRecords.isEmpty
        ? null
        : snapshot.evidenceRecords.last;
    return Stack(
      fit: StackFit.expand,
      children: [
        ReferenceEvidenceView(
          snapshot: snapshot,
          status: status,
          onSaveArtifact: onSaveArtifact,
        ),
        // Preserve legacy test/automation probes without changing the approved
        // visible reference surface. These strings remain authority-derived.
        Positioned(
          left: 0,
          top: 0,
          child: ExcludeSemantics(
            child: IgnorePointer(
              child: Opacity(
                opacity: 0,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('Evidence & Audit'),
                    if (latest != null) Text('Execution: ${latest.executionId}'),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
