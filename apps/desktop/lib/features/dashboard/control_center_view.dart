import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';

class ControlCenterView extends StatelessWidget {
  const ControlCenterView({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final VoidCallback? onRefreshRequested;

  String _count(int? value) => value?.toString() ?? '—';

  int _listLength(Map<String, Object?> source, String key) {
    final value = source[key];
    return value is List<Object?> ? value.length : 0;
  }

  @override
  Widget build(BuildContext context) {
    final leaseCount = _listLength(operationalSnapshot.schedulerState, 'leases');
    final effectCount = _listLength(operationalSnapshot.schedulerState, 'effects');

    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1500),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Control Center',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              const Text(
                'Authoritative execution visibility for ILAIOS operations.',
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  _MetricCard(
                    label: 'Goals',
                    value: _count(projection.goalCount),
                    icon: Icons.flag_outlined,
                  ),
                  _MetricCard(
                    label: 'Jobs',
                    value: _count(projection.jobCount),
                    icon: Icons.work_outline,
                  ),
                  _MetricCard(
                    label: 'Live events',
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.liveEventCount}'
                        : '—',
                    icon: Icons.bolt_outlined,
                  ),
                  _MetricCard(
                    label: 'Runtime routes',
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.runtimeRouteCount}'
                        : '—',
                    icon: Icons.route_outlined,
                  ),
                  _MetricCard(
                    label: 'Evidence',
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.evidenceCount}'
                        : '—',
                    icon: Icons.fact_check_outlined,
                  ),
                  _MetricCard(
                    label: 'Schema',
                    value: projection.schemaVersion ?? '—',
                    icon: Icons.schema_outlined,
                  ),
                ],
              ),
              const SizedBox(height: 20),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 900;
                  final execution = _ExecutionPanel(
                    projection: projection,
                    operationalStatus: operationalStatus,
                    leaseCount: leaseCount,
                    effectCount: effectCount,
                    onRefreshRequested: onRefreshRequested,
                  );
                  final governance = _GovernanceSummary(
                    operationalSnapshot: operationalSnapshot,
                  );
                  if (!wide) {
                    return Column(
                      children: [
                        execution,
                        const SizedBox(height: 16),
                        governance,
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 2, child: execution),
                      const SizedBox(width: 16),
                      Expanded(child: governance),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        width: 220,
        height: 116,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: IlaiosTheme.primary.withValues(alpha: .12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: IlaiosTheme.cyan),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        color: IlaiosTheme.muted,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExecutionPanel extends StatelessWidget {
  const _ExecutionPanel({
    required this.projection,
    required this.operationalStatus,
    required this.leaseCount,
    required this.effectCount,
    this.onRefreshRequested,
  });

  final ControlPlaneProjection projection;
  final String operationalStatus;
  final int leaseCount;
  final int effectCount;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.monitor_heart_outlined, color: IlaiosTheme.cyan),
                SizedBox(width: 10),
                Text(
                  'Live Execution',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Semantics(
              label: 'Control plane connection status',
              child: Text(
                projection.status,
                key: const Key('connection-status'),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              operationalStatus,
              key: const Key('operational-status'),
              style: const TextStyle(color: IlaiosTheme.muted),
            ),
            const SizedBox(height: 18),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: IlaiosTheme.canvas,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: IlaiosTheme.border),
              ),
              child: projection.connected
                  ? Row(
                      children: [
                        Expanded(child: _InlineStat(label: 'Leases', value: '$leaseCount')),
                        Expanded(child: _InlineStat(label: 'Effects', value: '$effectCount')),
                      ],
                    )
                  : const Text(
                      'No authoritative execution state available. ILAIOS Desktop will not fabricate jobs, agents, logs, or progress.',
                      style: TextStyle(color: IlaiosTheme.muted, height: 1.5),
                    ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              key: const Key('refresh-command'),
              onPressed: projection.connected ? onRefreshRequested : null,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh authoritative state'),
            ),
          ],
        ),
      ),
    );
  }
}

class _InlineStat extends StatelessWidget {
  const _InlineStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12)),
        const SizedBox(height: 5),
        Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
      ],
    );
  }
}

class _GovernanceSummary extends StatelessWidget {
  const _GovernanceSummary({required this.operationalSnapshot});

  final OperationalSnapshot operationalSnapshot;

  int _listLength(String key) {
    final value = operationalSnapshot.grantsState[key];
    return value is List<Object?> ? value.length : 0;
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.shield_outlined, color: IlaiosTheme.cyan),
                SizedBox(width: 10),
                Text(
                  'Governance',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 18),
            const _GovernanceRow(label: 'Authority', value: 'Backend / control plane'),
            const _GovernanceRow(label: 'Client mode', value: 'Projection only'),
            _GovernanceRow(label: 'Registered grants', value: '${_listLength('grants')}'),
            _GovernanceRow(label: 'Revoked grants', value: '${_listLength('revoked')}'),
            _GovernanceRow(label: 'Stopped subjects', value: '${_listLength('stopped')}'),
          ],
        ),
      ),
    );
  }
}

class _GovernanceRow extends StatelessWidget {
  const _GovernanceRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
