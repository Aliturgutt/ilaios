import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'reference_workflows_view.dart';

/// Compatibility entry point for the Workflows destination.
///
/// The Workflows page is rendered by [ReferenceWorkflowsView]. Canonical shells
/// provide [onNavigate] so in-surface actions use the persistent Desktop
/// navigation. The visual-repair summary layer presents five distinct cards
/// using only authority-derived counts; it does not create workflow state.
class ControlCenterView extends StatelessWidget {
  const ControlCenterView({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.onRefreshRequested,
    this.onNavigate,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final VoidCallback? onRefreshRequested;
  final ValueChanged<DesktopSection>? onNavigate;

  @override
  Widget build(BuildContext context) {
    final underlyingProjection = ControlPlaneProjection(
      connected: projection.connected,
      status: projection.status,
      goalCount: projection.goalCount,
      jobCount: null,
      lastEvent: projection.lastEvent,
      schemaVersion: projection.schemaVersion,
    );

    return Stack(
      children: [
        Positioned.fill(
          child: ReferenceWorkflowsView(
            projection: underlyingProjection,
            snapshot: operationalSnapshot,
            status: operationalStatus,
            onRefreshRequested: onRefreshRequested,
            onNavigate:
                onNavigate ?? (section) => _navigationNotice(context, section),
          ),
        ),
        Positioned(
          left: 14,
          right: 12,
          top: 60,
          height: 50,
          child: IgnorePointer(
            child: _WorkflowSummaryCards(
              projection: projection,
              snapshot: operationalSnapshot,
            ),
          ),
        ),
      ],
    );
  }

  void _navigationNotice(BuildContext context, DesktopSection section) {
    final label = section.localizedLabel(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '$label: use the persistent Desktop navigation to open this destination.',
        ),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}

class _WorkflowSummaryCards extends StatelessWidget {
  const _WorkflowSummaryCards({
    required this.projection,
    required this.snapshot,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    final items = <({String id, String label, String value})>[
      (
        id: 'total',
        label: tr ? 'Toplam' : 'Total',
        value: projection.jobCount?.toString() ?? '—',
      ),
      (
        id: 'active',
        label: tr ? 'Aktif' : 'Active',
        value: _authoritativeInt(snapshot.schedulerState, const [
              'active_count',
              'active_jobs',
              'running_count',
            ])?.toString() ??
            '—',
      ),
      (
        id: 'approval',
        label: tr ? 'Onay Bekleyen' : 'Awaiting Approval',
        value: _authoritativeListCount(snapshot.governanceState, 'work')
                ?.toString() ??
            '—',
      ),
      (
        id: 'overdue',
        label: tr ? 'Geciken' : 'Overdue',
        value: _authoritativeInt(snapshot.schedulerState, const [
              'overdue_count',
              'late_count',
            ])?.toString() ??
            '—',
      ),
      (
        id: 'completed',
        label: tr ? 'Tamamlanan' : 'Completed',
        value: _authoritativeInt(snapshot.schedulerState, const [
              'completed_count',
              'completed_jobs',
              'done_count',
            ])?.toString() ??
            '—',
      ),
    ];

    return Container(
      color: Theme.of(context).scaffoldBackgroundColor,
      child: Row(
        children: [
          for (var index = 0; index < items.length; index++) ...[
            if (index > 0) const SizedBox(width: 8),
            Expanded(
              child: Container(
                key: ValueKey('workflows-summary-${items[index].id}'),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerLowest,
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        items[index].label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 8.4,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      items[index].value,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

int? _authoritativeInt(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is int) return value;
    if (value is num) return value.round();
  }
  return null;
}

int? _authoritativeListCount(Map<String, Object?> source, String key) {
  if (!source.containsKey(key)) return null;
  final value = source[key];
  return value is List<Object?> ? value.length : null;
}
