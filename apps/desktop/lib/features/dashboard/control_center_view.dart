import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_surface_catalog.dart';
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
              Text(
                _surface(context, 'control.title'),
                style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Text(_surface(context, 'control.subtitle')),
              const SizedBox(height: 24),
              Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  _MetricCard(
                    label: _surface(context, 'control.goals'),
                    value: _count(projection.goalCount),
                    icon: Icons.flag_outlined,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.jobs'),
                    value: _count(projection.jobCount),
                    icon: Icons.work_outline,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.liveEvents'),
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.liveEventCount}'
                        : '—',
                    icon: Icons.bolt_outlined,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.runtimeRoutes'),
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.runtimeRouteCount}'
                        : '—',
                    icon: Icons.route_outlined,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.evidence'),
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.evidenceCount}'
                        : '—',
                    icon: Icons.fact_check_outlined,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.schema'),
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
            Row(
              children: [
                const Icon(Icons.monitor_heart_outlined, color: IlaiosTheme.cyan),
                const SizedBox(width: 10),
                Text(
                  _surface(context, 'control.liveExecution'),
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Semantics(
              label: _surface(context, 'control.connectionStatus'),
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
                        Expanded(
                          child: _InlineStat(
                            label: _surface(context, 'control.leases'),
                            value: '$leaseCount',
                          ),
                        ),
                        Expanded(
                          child: _InlineStat(
                            label: _surface(context, 'control.effects'),
                            value: '$effectCount',
                          ),
                        ),
                      ],
                    )
                  : Text(
                      _surface(context, 'control.noExecution'),
                      style: const TextStyle(color: IlaiosTheme.muted, height: 1.5),
                    ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              key: const Key('refresh-command'),
              onPressed: projection.connected ? onRefreshRequested : null,
              icon: const Icon(Icons.refresh),
              label: Text(_surface(context, 'control.refresh')),
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
            Row(
              children: [
                const Icon(Icons.shield_outlined, color: IlaiosTheme.cyan),
                const SizedBox(width: 10),
                Text(
                  _surface(context, 'control.governance'),
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 18),
            _GovernanceRow(
              label: _surface(context, 'control.authority'),
              value: _surface(context, 'control.backendAuthority'),
            ),
            _GovernanceRow(
              label: _surface(context, 'control.clientMode'),
              value: _surface(context, 'control.projectionOnly'),
            ),
            _GovernanceRow(
              label: _surface(context, 'control.registeredGrants'),
              value: '${_listLength('grants')}',
            ),
            _GovernanceRow(
              label: _surface(context, 'control.revokedGrants'),
              value: '${_listLength('revoked')}',
            ),
            _GovernanceRow(
              label: _surface(context, 'control.stoppedSubjects'),
              value: '${_listLength('stopped')}',
            ),
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

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;
