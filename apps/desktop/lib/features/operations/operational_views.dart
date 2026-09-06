import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
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
/// Search and filtering are presentation-only operations over the local
/// authoritative evidence projection. They never mutate Evidence records or
/// create a second evidence taxonomy/authority.
class EvidenceView extends StatefulWidget {
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
  State<EvidenceView> createState() => _EvidenceViewState();
}

class _EvidenceViewState extends State<EvidenceView> {
  static const _all = '__all__';

  final TextEditingController _searchController = TextEditingController();
  String _query = '';
  String _action = _all;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    final actions = widget.snapshot.evidenceRecords
        .map((record) => record.action.trim())
        .where((value) => value.isNotEmpty)
        .toSet()
        .toList(growable: false)
      ..sort();
    final effectiveAction = actions.contains(_action) ? _action : _all;
    final query = _query.trim().toLowerCase();
    final filtered = widget.snapshot.evidenceRecords.where((record) {
      final actionMatches =
          effectiveAction == _all || record.action == effectiveAction;
      if (!actionMatches) return false;
      if (query.isEmpty) return true;
      return '${record.sequence} ${record.executionId} ${record.artifactDigest} '
              '${record.action} ${record.previousHash} ${record.recordHash}'
          .toLowerCase()
          .contains(query);
    }).toList(growable: false);

    final filteredSnapshot = OperationalSnapshot(
      runtimeRoutes: widget.snapshot.runtimeRoutes,
      schedulerState: widget.snapshot.schedulerState,
      grantsState: widget.snapshot.grantsState,
      governanceState: widget.snapshot.governanceState,
      evidenceRecords: filtered,
      liveEvents: widget.snapshot.liveEvents,
      agentState: widget.snapshot.agentState,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 0),
          child: Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 38,
                  child: TextField(
                    key: const Key('evidence-search'),
                    controller: _searchController,
                    onChanged: (value) => setState(() => _query = value),
                    decoration: InputDecoration(
                      isDense: true,
                      prefixIcon: const Icon(Icons.search_rounded, size: 17),
                      hintText: tr ? 'Kanıtlarda ara' : 'Search evidence',
                      border: const OutlineInputBorder(),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                key: const Key('evidence-filter'),
                width: 210,
                height: 38,
                child: DropdownButtonFormField<String>(
                  initialValue: effectiveAction,
                  isExpanded: true,
                  decoration: InputDecoration(
                    isDense: true,
                    prefixIcon: const Icon(Icons.filter_list_rounded, size: 17),
                    border: const OutlineInputBorder(),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                  ),
                  items: [
                    DropdownMenuItem<String>(
                      value: _all,
                      child: Text(tr ? 'Tüm kanıt türleri' : 'All evidence types'),
                    ),
                    for (final action in actions)
                      DropdownMenuItem<String>(
                        value: action,
                        child: Text(
                          action,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  onChanged: (value) => setState(() => _action = value ?? _all),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 2),
        Expanded(
          child: ReferenceEvidenceView(
            snapshot: filteredSnapshot,
            status: widget.status,
            onSaveArtifact: widget.onSaveArtifact,
          ),
        ),
      ],
    );
  }
}
