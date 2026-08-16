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
      padding: const EdgeInsets.all(24),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1500),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: IlaiosTheme.coreBlue.withValues(alpha: .12),
                      borderRadius: BorderRadius.circular(13),
                    ),
                    child: const Icon(
                      Icons.account_tree_outlined,
                      color: IlaiosTheme.coreBlue,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _surface(context, 'control.title'),
                          style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          _surface(context, 'control.subtitle'),
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    key: const Key('refresh-command'),
                    tooltip: _surface(context, 'control.refresh'),
                    onPressed: projection.connected ? onRefreshRequested : null,
                    style: IconButton.styleFrom(
                      backgroundColor: IlaiosTheme.enterpriseCyan.withValues(alpha: .10),
                      side: BorderSide(
                        color: IlaiosTheme.enterpriseCyan.withValues(alpha: .32),
                      ),
                    ),
                    icon: const Icon(
                      Icons.refresh,
                      color: IlaiosTheme.enterpriseCyan,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _MetricCard(
                    label: _surface(context, 'control.goals'),
                    value: _count(projection.goalCount),
                    icon: Icons.flag_outlined,
                    accent: IlaiosTheme.enterpriseCyan,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.jobs'),
                    value: _count(projection.jobCount),
                    icon: Icons.work_outline,
                    accent: IlaiosTheme.coreBlue,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.liveEvents'),
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.liveEventCount}'
                        : '—',
                    icon: Icons.bolt_outlined,
                    accent: IlaiosTheme.violet,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.runtimeRoutes'),
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.runtimeRouteCount}'
                        : '—',
                    icon: Icons.route_outlined,
                    accent: IlaiosTheme.coreBlue,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.evidence'),
                    value: operationalSnapshot.available
                        ? '${operationalSnapshot.evidenceCount}'
                        : '—',
                    icon: Icons.fact_check_outlined,
                    accent: IlaiosTheme.enterpriseCyan,
                  ),
                  _MetricCard(
                    label: _surface(context, 'control.schema'),
                    value: projection.schemaVersion ?? '—',
                    icon: Icons.schema_outlined,
                    accent: IlaiosTheme.violet,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              LayoutBuilder(
                builder: (context, constraints) {
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
                  if (constraints.maxWidth < 880) {
                    return Column(
                      children: [
                        execution,
                        const SizedBox(height: 14),
                        governance,
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 2, child: execution),
                      const SizedBox(width: 14),
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

class _MetricCard extends StatefulWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  State<_MetricCard> createState() => _MetricCardState();
}

class _MetricCardState extends State<_MetricCard> {
  bool hovered = false;

  @override
  Widget build(BuildContext context) => MouseRegion(
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: Material(
          color: hovered
              ? widget.accent.withValues(alpha: .08)
              : Theme.of(context).colorScheme.surfaceContainerLow,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(13),
            side: BorderSide(
              color: hovered
                  ? widget.accent.withValues(alpha: .55)
                  : Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => _showMetric(context, widget.label, widget.value, widget.icon, widget.accent),
            child: SizedBox(
              width: 220,
              height: 116,
              child: Padding(
                padding: const EdgeInsets.all(15),
                child: Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: widget.accent.withValues(alpha: .13),
                        borderRadius: BorderRadius.circular(11),
                      ),
                      child: Icon(widget.icon, color: widget.accent),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.label,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            widget.value,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
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
  Widget build(BuildContext context) => _Panel(
        accent: IlaiosTheme.enterpriseCyan,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.monitor_heart_outlined,
                  color: IlaiosTheme.enterpriseCyan,
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    _surface(context, 'control.liveExecution'),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Semantics(
              label: _surface(context, 'control.connectionStatus'),
              child: Text(
                _localizedStatus(context, projection.status),
                key: const Key('connection-status'),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            const SizedBox(height: 5),
            Text(
              _localizedStatus(context, operationalStatus),
              key: const Key('operational-status'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLowest,
                borderRadius: BorderRadius.circular(11),
                border: Border.all(
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
              child: projection.connected
                  ? Row(
                      children: [
                        Expanded(
                          child: _InlineStat(
                            label: _surface(context, 'control.leases'),
                            value: '$leaseCount',
                            accent: IlaiosTheme.violet,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _InlineStat(
                            label: _surface(context, 'control.effects'),
                            value: '$effectCount',
                            accent: IlaiosTheme.coreBlue,
                          ),
                        ),
                      ],
                    )
                  : Text(
                      _surface(context, 'control.noExecution'),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
            ),
            if (projection.connected && leaseCount == 0 && effectCount == 0) ...[
              const SizedBox(height: 12),
              Text(
                _isTr(context)
                    ? 'Henüz aktif yürütme yok. Yeni bir hedef kabul edildiğinde bu görünüm yetkili çalışma zamanı durumuyla otomatik güncellenir.'
                    : 'No execution is active yet. This view updates from authoritative runtime state when a new goal is accepted.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 14),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.icon(
                onPressed: projection.connected ? onRefreshRequested : null,
                icon: const Icon(Icons.refresh),
                label: Text(_surface(context, 'control.refresh')),
              ),
            ),
          ],
        ),
      );
}

class _InlineStat extends StatelessWidget {
  const _InlineStat({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: .06),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 5),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: accent,
                    fontWeight: FontWeight.w800,
                  ),
            ),
          ],
        ),
      );
}

class _GovernanceSummary extends StatelessWidget {
  const _GovernanceSummary({required this.operationalSnapshot});

  final OperationalSnapshot operationalSnapshot;

  int _listLength(String key) {
    final value = operationalSnapshot.grantsState[key];
    return value is List<Object?> ? value.length : 0;
  }

  @override
  Widget build(BuildContext context) => _Panel(
        accent: IlaiosTheme.violet,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(Icons.shield_outlined, color: IlaiosTheme.violet),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    _surface(context, 'control.governance'),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
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
      );
}

class _GovernanceRow extends StatelessWidget {
  const _GovernanceRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.bodySmall),
            ),
            const SizedBox(width: 12),
            Flexible(
              child: Text(
                value,
                textAlign: TextAlign.right,
                style: Theme.of(context).textTheme.labelMedium,
              ),
            ),
          ],
        ),
      );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.accent, required this.child});

  final Color accent;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: accent.withValues(alpha: .20)),
        ),
        child: child,
      );
}

Future<void> _showMetric(
  BuildContext context,
  String label,
  String value,
  IconData icon,
  Color accent,
) => showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: Icon(icon, color: accent),
        title: Text(label),
        content: SelectableText(value),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_isTr(context) ? 'Kapat' : 'Close'),
          ),
        ],
      ),
    );

String _localizedStatus(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    _ => value,
  };
}

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;
