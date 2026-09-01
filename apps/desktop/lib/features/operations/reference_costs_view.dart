import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';

/// Reference-faithful Costs surface for the approved dark/light Desktop UI.
///
/// The supplied screenshots define presentation only. All monetary values,
/// usage values, alerts, recommendations, reports and series rendered here
/// come from the authenticated operational snapshot. Missing telemetry is
/// shown as unavailable rather than copied from the visual reference.
class ReferenceCostsView extends StatelessWidget {
  const ReferenceCostsView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  Widget build(BuildContext context) {
    final model = _CostModel.fromSnapshot(snapshot);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (!model.hasAnyTelemetry) {
      return Container(
        key: const Key('reference-costs-page'),
        color: Theme.of(context).scaffoldBackgroundColor,
        padding: const EdgeInsets.fromLTRB(18, 13, 18, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Header(model: model),
            const SizedBox(height: 18),
            Expanded(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 520),
                  child: Container(
                    padding: const EdgeInsets.all(22),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerLow,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.account_balance_wallet_outlined,
                          size: 30,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(height: 10),
                        Text(
                          _copy(
                            context,
                            'Cost data is not available yet',
                            'Maliyet verisi henüz mevcut değil',
                          ),
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          _copy(
                            context,
                            'Costs appear here when authoritative provider or execution telemetry is available.',
                            'Yetkili sağlayıcı veya yürütme maliyet telemetrisi mevcut olduğunda burada gösterilir.',
                          ),
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      key: const Key('reference-costs-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(18, 13, 18, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Header(model: model),
          const SizedBox(height: 10),
          SizedBox(
            key: const Key('costs-summary-strip'),
            height: 102,
            child: Row(
              children: [
                Expanded(
                  child: _MetricCard(
                    title: _copy(context, 'Total Cost', 'Toplam Maliyet'),
                    value: model.totalUsdText(context),
                    icon: Icons.account_balance_wallet_outlined,
                    accent: IlaiosTheme.coreBlue,
                    detail: model.totalDelta,
                  ),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: _MetricCard(
                    title: _copy(context, 'Forecast This Month', 'Tahmini Son Ay Maliyeti'),
                    value: model.forecastUsdText(context),
                    icon: Icons.show_chart,
                    accent: IlaiosTheme.enterpriseCyan,
                    detail: model.forecastDelta,
                  ),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: _BudgetMetricCard(model: model),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: _MetricCard(
                    title: _copy(context, 'Savings (This Month)', 'Tasarruf (Bu Ay)'),
                    value: model.savingsUsdText(context),
                    icon: Icons.savings_outlined,
                    accent: IlaiosTheme.warning,
                    detail: model.savingsDelta,
                  ),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: _MetricCard(
                    title: _copy(context, 'Forecast Next Month', 'Tahmini Sonraki Ay'),
                    value: model.nextMonthUsdText(context),
                    icon: Icons.calendar_month_outlined,
                    accent: IlaiosTheme.violet,
                    detail: model.nextMonthDelta,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  flex: 74,
                  child: Column(
                    children: [
                      Expanded(
                        flex: 48,
                        child: Row(
                          children: [
                            Expanded(
                              flex: 56,
                              child: _TrendPanel(model: model),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              flex: 44,
                              child: _DistributionPanel(model: model),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                      Expanded(
                        flex: 52,
                        child: _ResourcesPanel(model: model),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  flex: 26,
                  child: Column(
                    children: [
                      Expanded(child: _AlertsPanel(model: model)),
                      const SizedBox(height: 10),
                      Expanded(child: _RecommendationsPanel(model: model)),
                      const SizedBox(height: 10),
                      Expanded(child: _ReportsPanel(model: model)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (!model.hasAnyTelemetry) ...[
            const SizedBox(height: 8),
            _TruthNotice(status: status, isDark: isDark),
          ],
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _copy(context, 'Costs', 'Maliyetler'),
                  style: const TextStyle(
                    fontSize: 21,
                    height: 1.1,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  _copy(
                    context,
                    'Monitor infrastructure, service and resource usage costs.',
                    'Altyapı, servis ve kaynak kullanım maliyetlerinizi izleyin ve yönetin.',
                  ),
                  style: TextStyle(
                    fontSize: 9.5,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          if (model.periodLabel != null) ...[
            _ToolbarButton(
              icon: Icons.date_range_outlined,
              label: model.periodLabel!,
            ),
            const SizedBox(width: 8),
          ],
          _ToolbarButton(
            icon: Icons.ios_share_outlined,
            label: _copy(context, 'Export', 'Dışa Aktar'),
            enabled: model.hasAnyTelemetry,
          ),
        ],
      );
}

class _ToolbarButton extends StatelessWidget {
  const _ToolbarButton({required this.icon, required this.label, this.enabled = true});

  final IconData icon;
  final String label;
  final bool enabled;

  @override
  Widget build(BuildContext context) => Container(
        height: 33,
        padding: const EdgeInsets.symmetric(horizontal: 11),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color: enabled
                  ? Theme.of(context).colorScheme.onSurface
                  : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: 7),
            Text(
              label,
              style: TextStyle(
                fontSize: 9.5,
                fontWeight: FontWeight.w600,
                color: enabled
                    ? Theme.of(context).colorScheme.onSurface
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.accent,
    this.detail,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color accent;
  final String? detail;

  @override
  Widget build(BuildContext context) => _Panel(
        padding: const EdgeInsets.fromLTRB(13, 12, 12, 10),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600)),
                  const Spacer(),
                  Text(
                    value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    detail ?? _copy(context, 'No comparison telemetry', 'Karşılaştırma telemetrisi yok'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 8.5,
                      color: detail == null
                          ? Theme.of(context).colorScheme.onSurfaceVariant
                          : IlaiosTheme.success,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              width: 45,
              height: 45,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: .11),
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: Icon(icon, size: 22, color: accent),
            ),
          ],
        ),
      );
}

class _BudgetMetricCard extends StatelessWidget {
  const _BudgetMetricCard({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) {
    final pct = model.budgetUsagePercent;
    return _Panel(
      padding: const EdgeInsets.fromLTRB(13, 12, 12, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _copy(context, 'Budget Usage', 'Bütçe Kullanımı'),
            style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600),
          ),
          const Spacer(),
          Row(
            children: [
              Expanded(
                child: Text(
                  pct == null ? context.tr('common.unavailable') : '${pct.round()}%',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                ),
              ),
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: IlaiosTheme.success.withValues(alpha: .11),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.pie_chart_outline, color: IlaiosTheme.success, size: 21),
              ),
            ],
          ),
          const SizedBox(height: 5),
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: LinearProgressIndicator(
              minHeight: 5,
              value: pct == null ? 0 : (pct / 100).clamp(0, 1),
              color: IlaiosTheme.coreBlue,
              backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            model.budgetPairText(context),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 8,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _TrendPanel extends StatelessWidget {
  const _TrendPanel({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('costs-trend-panel'),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    _copy(context, 'Cost Trend', 'Maliyet Trendi'),
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
                  ),
                ),
                _TinyChip(label: _copy(context, 'Daily', 'Günlük')),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: model.trend.isEmpty
                  ? _EmptyPanel(
                      icon: Icons.show_chart,
                      text: _copy(context, 'Cost trend telemetry unavailable', 'Maliyet trendi telemetrisi kullanılamıyor'),
                    )
                  : _TrendChart(points: model.trend),
            ),
            if (model.trend.isNotEmpty) ...[
              const SizedBox(height: 5),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const _LegendDot(color: IlaiosTheme.coreBlue),
                  const SizedBox(width: 5),
                  Text(
                    _copy(context, 'Total Cost (USD)', 'Toplam Maliyet (USD)'),
                    style: TextStyle(fontSize: 8, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ],
          ],
        ),
      );
}

class _DistributionPanel extends StatelessWidget {
  const _DistributionPanel({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('costs-distribution-panel'),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 9),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    _copy(context, 'Cost Distribution (By Service)', 'Maliyet Dağılımı (Hizmet Bazlı)'),
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
                  ),
                ),
                Text(
                  model.totalUsdText(context),
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Expanded(
              child: model.distribution.isEmpty
                  ? _EmptyPanel(
                      icon: Icons.donut_large_outlined,
                      text: _copy(context, 'Service cost telemetry unavailable', 'Hizmet maliyeti telemetrisi kullanılamıyor'),
                    )
                  : Row(
                      children: [
                        Expanded(
                          flex: 44,
                          child: _DonutChart(items: model.distribution, total: model.totalUsd),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 56,
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              for (final item in model.distribution.take(6))
                                Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 2),
                                  child: Row(
                                    children: [
                                      _LegendDot(color: item.color),
                                      const SizedBox(width: 6),
                                      Expanded(
                                        child: Text(
                                          item.label,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(fontSize: 8.5),
                                        ),
                                      ),
                                      Text(
                                        _currency(item.value),
                                        style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),
                                      ),
                                    ],
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
            ),
          ],
        ),
      );
}

class _ResourcesPanel extends StatelessWidget {
  const _ResourcesPanel({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('costs-resources-panel'),
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 8),
              child: Text(
                _copy(context, 'Highest Cost Resources', 'En Yüksek Maliyeti Oluşturan Kaynaklar'),
                style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
              ),
            ),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            if (model.resources.isEmpty)
              Expanded(
                child: _EmptyPanel(
                  icon: Icons.table_rows_outlined,
                  text: _copy(context, 'Resource-level cost telemetry unavailable', 'Kaynak düzeyi maliyet telemetrisi kullanılamıyor'),
                ),
              )
            else ...[
              _ResourceHeader(),
              Expanded(
                child: Column(
                  children: [
                    for (final item in model.resources.take(5)) Expanded(child: _ResourceRow(item: item)),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                child: Row(
                  children: [
                    Text(
                      '${math.min(5, model.resources.length)} / ${model.resources.length}',
                      style: TextStyle(fontSize: 8, color: Theme.of(context).colorScheme.onSurfaceVariant),
                    ),
                    const Spacer(),
                    Text(
                      _copy(context, 'View all resources →', 'Tüm Kaynakları Görüntüle →'),
                      style: const TextStyle(fontSize: 8.5, color: IlaiosTheme.coreBlue, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      );
}

class _ResourceHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        height: 27,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        color: Theme.of(context).colorScheme.surfaceContainer,
        child: Row(
          children: [
            _header(context, _copy(context, 'Resource', 'Kaynak'), flex: 22),
            _header(context, _copy(context, 'Type', 'Tür'), flex: 17),
            _header(context, _copy(context, 'Service', 'Servis'), flex: 17),
            _header(context, _copy(context, 'Usage', 'Kullanım'), flex: 16),
            _header(context, _copy(context, 'Cost (USD)', 'Maliyet (USD)'), flex: 16),
            _header(context, _copy(context, 'Change', 'Değişim'), flex: 12),
          ],
        ),
      );

  Widget _header(BuildContext context, String text, {required int flex}) => Expanded(
        flex: flex,
        child: Text(
          text,
          style: TextStyle(fontSize: 7.8, color: Theme.of(context).colorScheme.onSurfaceVariant),
        ),
      );
}

class _ResourceRow extends StatelessWidget {
  const _ResourceRow({required this.item});

  final _ResourceCost item;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant.withValues(alpha: .75))),
        ),
        child: Row(
          children: [
            Expanded(
              flex: 22,
              child: Row(
                children: [
                  Container(
                    width: 18,
                    height: 18,
                    decoration: BoxDecoration(
                      color: IlaiosTheme.coreBlue.withValues(alpha: .12),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Icon(Icons.hexagon_outlined, size: 11, color: IlaiosTheme.coreBlue),
                  ),
                  const SizedBox(width: 7),
                  Expanded(child: _cell(item.name)),
                ],
              ),
            ),
            Expanded(flex: 17, child: _cell(item.type ?? '—')),
            Expanded(flex: 17, child: _cell(item.service ?? '—')),
            Expanded(flex: 16, child: _cell(item.usage ?? '—')),
            Expanded(flex: 16, child: _cell(item.cost == null ? '—' : _currency(item.cost!))),
            Expanded(
              flex: 12,
              child: Text(
                item.change ?? '—',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 8.2,
                  fontWeight: FontWeight.w600,
                  color: item.change == null ? Theme.of(context).colorScheme.onSurfaceVariant : IlaiosTheme.success,
                ),
              ),
            ),
          ],
        ),
      );

  Widget _cell(String text) => Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 8.2),
      );
}

class _AlertsPanel extends StatelessWidget {
  const _AlertsPanel({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) => _SideListPanel(
        key: const Key('costs-alerts-panel'),
        title: _copy(context, 'Budget Alerts', 'Bütçe Uyarıları'),
        icon: Icons.warning_amber_rounded,
        accent: IlaiosTheme.warning,
        emptyText: _copy(context, 'No authoritative budget alerts', 'Yetkili bütçe uyarısı yok'),
        rows: [
          for (final item in model.alerts)
            _SideRow(title: item.title, subtitle: item.subtitle, trailing: item.when),
        ],
      );
}

class _RecommendationsPanel extends StatelessWidget {
  const _RecommendationsPanel({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) => _SideListPanel(
        key: const Key('costs-recommendations-panel'),
        title: _copy(context, 'Cost Optimization Suggestions', 'Maliyet Optimizasyon Önerileri'),
        icon: Icons.eco_outlined,
        accent: IlaiosTheme.success,
        emptyText: _copy(context, 'No authoritative optimization suggestions', 'Yetkili optimizasyon önerisi yok'),
        rows: [
          for (final item in model.recommendations)
            _SideRow(title: item.title, subtitle: item.subtitle, trailing: item.value),
        ],
      );
}

class _ReportsPanel extends StatelessWidget {
  const _ReportsPanel({required this.model});

  final _CostModel model;

  @override
  Widget build(BuildContext context) => _SideListPanel(
        key: const Key('costs-reports-panel'),
        title: _copy(context, 'Cost Reports', 'Maliyet Raporları'),
        icon: Icons.description_outlined,
        accent: IlaiosTheme.coreBlue,
        emptyText: _copy(context, 'No authoritative cost reports', 'Yetkili maliyet raporu yok'),
        rows: [
          for (final item in model.reports)
            _SideRow(title: item.title, subtitle: item.subtitle, trailing: item.value),
        ],
      );
}

class _SideListPanel extends StatelessWidget {
  const _SideListPanel({
    required this.title,
    required this.icon,
    required this.accent,
    required this.emptyText,
    required this.rows,
    super.key,
  });

  final String title;
  final IconData icon;
  final Color accent;
  final String emptyText;
  final List<_SideRow> rows;

  @override
  Widget build(BuildContext context) => _Panel(
        padding: const EdgeInsets.fromLTRB(11, 9, 11, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(title, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700)),
                ),
                Text(
                  _copy(context, 'All', 'Tümü'),
                  style: TextStyle(fontSize: 8, color: Theme.of(context).colorScheme.onSurfaceVariant),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Expanded(
              child: rows.isEmpty
                  ? _EmptyPanel(icon: icon, text: emptyText, compact: true)
                  : Column(
                      children: [
                        for (final row in rows.take(3)) Expanded(child: row),
                      ],
                    ),
            ),
            if (rows.isNotEmpty)
              Align(
                alignment: Alignment.center,
                child: Text(
                  _copy(context, 'View all →', 'Tümünü Görüntüle →'),
                  style: TextStyle(fontSize: 8.3, color: accent, fontWeight: FontWeight.w600),
                ),
              ),
          ],
        ),
      );
}

class _SideRow extends StatelessWidget {
  const _SideRow({required this.title, this.subtitle, this.trailing});

  final String title;
  final String? subtitle;
  final String? trailing;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              color: IlaiosTheme.coreBlue.withValues(alpha: .09),
              borderRadius: BorderRadius.circular(5),
            ),
            child: const Icon(Icons.circle_outlined, size: 11, color: IlaiosTheme.coreBlue),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 8.6, fontWeight: FontWeight.w600),
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 7.6, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 4),
            Text(
              trailing!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600),
            ),
          ],
        ],
      );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child, this.padding = const EdgeInsets.all(12), super.key});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
        padding: padding,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: child,
      );
}

class _EmptyPanel extends StatelessWidget {
  const _EmptyPanel({required this.icon, required this.text, this.compact = false});

  final IconData icon;
  final String text;
  final bool compact;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: compact ? 18 : 25, color: Theme.of(context).colorScheme.onSurfaceVariant),
            SizedBox(height: compact ? 3 : 7),
            Text(
              text,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: compact ? 7.6 : 8.5,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
}

class _TruthNotice extends StatelessWidget {
  const _TruthNotice({required this.status, required this.isDark});

  final String status;
  final bool isDark;

  @override
  Widget build(BuildContext context) => Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 11),
        decoration: BoxDecoration(
          color: IlaiosTheme.coreBlue.withValues(alpha: isDark ? .09 : .06),
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: IlaiosTheme.coreBlue.withValues(alpha: .25)),
        ),
        child: Row(
          children: [
            const Icon(Icons.info_outline, size: 15, color: IlaiosTheme.coreBlue),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _copy(
                  context,
                  'Authoritative cost telemetry is unavailable. No reference-image monetary values or usage values are fabricated. Runtime status: $status',
                  'Yetkili maliyet telemetrisi kullanılamıyor. Referans görseldeki para veya kullanım değerleri uydurulmaz. Çalışma zamanı durumu: $status',
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 8, color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
            ),
          ],
        ),
      );
}

class _TinyChip extends StatelessWidget {
  const _TinyChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        height: 24,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Text(label, style: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600)),
      );
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: 7,
        height: 7,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      );
}

class _TrendChart extends StatelessWidget {
  const _TrendChart({required this.points});

  final List<_TrendPoint> points;

  @override
  Widget build(BuildContext context) => CustomPaint(
        painter: _TrendPainter(
          points: points.map((e) => e.value).toList(growable: false),
          grid: Theme.of(context).colorScheme.outlineVariant,
          line: IlaiosTheme.coreBlue,
          fill: IlaiosTheme.coreBlue.withValues(alpha: .08),
        ),
        child: const SizedBox.expand(),
      );
}

class _TrendPainter extends CustomPainter {
  const _TrendPainter({required this.points, required this.grid, required this.line, required this.fill});

  final List<double> points;
  final Color grid;
  final Color line;
  final Color fill;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;
    final gridPaint = Paint()..color = grid.withValues(alpha: .65)..strokeWidth = .6;
    for (var i = 0; i <= 4; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }
    final minValue = points.reduce(math.min);
    final maxValue = points.reduce(math.max);
    final span = math.max(.0001, maxValue - minValue);
    final path = Path();
    for (var i = 0; i < points.length; i++) {
      final x = points.length == 1 ? size.width / 2 : size.width * i / (points.length - 1);
      final y = size.height - ((points[i] - minValue) / span) * (size.height * .84) - size.height * .08;
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    final area = Path.from(path)..lineTo(size.width, size.height)..lineTo(0, size.height)..close();
    canvas.drawPath(area, Paint()..color = fill);
    canvas.drawPath(path, Paint()..color = line..strokeWidth = 1.8..style = PaintingStyle.stroke);
    final dot = Paint()..color = line;
    for (var i = 0; i < points.length; i++) {
      final x = points.length == 1 ? size.width / 2 : size.width * i / (points.length - 1);
      final y = size.height - ((points[i] - minValue) / span) * (size.height * .84) - size.height * .08;
      canvas.drawCircle(Offset(x, y), 2.1, dot);
    }
  }

  @override
  bool shouldRepaint(covariant _TrendPainter oldDelegate) => oldDelegate.points != points;
}

class _DonutChart extends StatelessWidget {
  const _DonutChart({required this.items, required this.total});

  final List<_DistributionItem> items;
  final double? total;

  @override
  Widget build(BuildContext context) => Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            painter: _DonutPainter(items: items),
            child: const SizedBox.expand(),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                total == null ? '—' : _currency(total!),
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              ),
              Text(
                _copy(context, 'Total', 'Toplam'),
                style: TextStyle(fontSize: 7.5, color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ],
      );
}

class _DonutPainter extends CustomPainter {
  const _DonutPainter({required this.items});

  final List<_DistributionItem> items;

  @override
  void paint(Canvas canvas, Size size) {
    final total = items.fold<double>(0, (sum, item) => sum + math.max(0, item.value));
    if (total <= 0) return;
    final rect = Offset.zero & size;
    final stroke = math.min(size.width, size.height) * .13;
    var start = -math.pi / 2;
    for (final item in items) {
      final sweep = math.pi * 2 * item.value / total;
      canvas.drawArc(
        rect.deflate(stroke / 2 + 2),
        start,
        sweep,
        false,
        Paint()
          ..color = item.color
          ..style = PaintingStyle.stroke
          ..strokeWidth = stroke,
      );
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(covariant _DonutPainter oldDelegate) => oldDelegate.items != items;
}

class _CostModel {
  const _CostModel({
    required this.totalUsd,
    required this.forecastUsd,
    required this.budgetUsd,
    required this.savingsUsd,
    required this.nextMonthUsd,
    required this.periodLabel,
    required this.totalDelta,
    required this.forecastDelta,
    required this.savingsDelta,
    required this.nextMonthDelta,
    required this.trend,
    required this.distribution,
    required this.resources,
    required this.alerts,
    required this.recommendations,
    required this.reports,
  });

  final double? totalUsd;
  final double? forecastUsd;
  final double? budgetUsd;
  final double? savingsUsd;
  final double? nextMonthUsd;
  final String? periodLabel;
  final String? totalDelta;
  final String? forecastDelta;
  final String? savingsDelta;
  final String? nextMonthDelta;
  final List<_TrendPoint> trend;
  final List<_DistributionItem> distribution;
  final List<_ResourceCost> resources;
  final List<_ListItem> alerts;
  final List<_ListItem> recommendations;
  final List<_ListItem> reports;

  bool get hasAnyTelemetry =>
      totalUsd != null ||
      forecastUsd != null ||
      budgetUsd != null ||
      savingsUsd != null ||
      nextMonthUsd != null ||
      trend.isNotEmpty ||
      distribution.isNotEmpty ||
      resources.isNotEmpty ||
      alerts.isNotEmpty ||
      recommendations.isNotEmpty ||
      reports.isNotEmpty;

  double? get budgetUsagePercent {
    if (totalUsd == null || budgetUsd == null || budgetUsd! <= 0) return null;
    return totalUsd! / budgetUsd! * 100;
  }

  String totalUsdText(BuildContext context) => totalUsd == null ? context.tr('common.unavailable') : _currency(totalUsd!);
  String forecastUsdText(BuildContext context) => forecastUsd == null ? context.tr('common.unavailable') : _currency(forecastUsd!);
  String savingsUsdText(BuildContext context) => savingsUsd == null ? context.tr('common.unavailable') : _currency(savingsUsd!);
  String nextMonthUsdText(BuildContext context) => nextMonthUsd == null ? context.tr('common.unavailable') : _currency(nextMonthUsd!);

  String budgetPairText(BuildContext context) {
    if (totalUsd == null || budgetUsd == null) return context.tr('common.unavailable');
    return '${_currency(totalUsd!)} / ${_currency(budgetUsd!)}';
  }

  static _CostModel fromSnapshot(OperationalSnapshot snapshot) {
    final roots = <Map<String, Object?>>[
      snapshot.governanceState,
      snapshot.schedulerState,
      ..._nestedMaps(snapshot.governanceState, const ['costs', 'finops', 'cost_telemetry']),
      ..._nestedMaps(snapshot.schedulerState, const ['costs', 'finops', 'cost_telemetry']),
    ];

    final total = _firstNumber(roots, const ['total_cost_usd', 'cost_usd', 'current_cost_usd', 'spend_usd']);
    final forecast = _firstNumber(roots, const ['forecast_cost_usd', 'estimated_month_cost_usd', 'forecast_usd']);
    final budget = _firstNumber(roots, const ['budget_usd', 'hard_cap_usd', 'monthly_budget_usd']);
    final savings = _firstNumber(roots, const ['savings_usd', 'optimized_savings_usd', 'monthly_savings_usd']);
    final next = _firstNumber(roots, const ['next_month_forecast_usd', 'next_month_cost_usd']);

    final trendMaps = _firstList(roots, const ['cost_trend', 'trend', 'daily_costs']);
    final trend = <_TrendPoint>[
      for (final item in trendMaps)
        if (_numberFromMap(item, const ['cost_usd', 'value', 'amount_usd', 'cost']) case final value?)
          _TrendPoint(
            label: _textFromMap(item, const ['date', 'label', 'day']) ?? '',
            value: value,
          ),
    ];

    final colors = <Color>[
      IlaiosTheme.coreBlue,
      const Color(0xFFFF3659),
      IlaiosTheme.danger,
      const Color(0xFF376BC5),
      const Color(0xFF358FD9),
      IlaiosTheme.violet,
      IlaiosTheme.warning,
      IlaiosTheme.success,
    ];
    final distributionMaps = _firstList(roots, const ['service_costs', 'cost_distribution', 'services']);
    final distribution = <_DistributionItem>[];
    for (var i = 0; i < distributionMaps.length; i++) {
      final item = distributionMaps[i];
      final value = _numberFromMap(item, const ['cost_usd', 'value', 'amount_usd', 'cost']);
      final label = _textFromMap(item, const ['service', 'name', 'label', 'category']);
      if (value != null && label != null) {
        distribution.add(_DistributionItem(label: label, value: value, color: colors[i % colors.length]));
      }
    }

    final resourceMaps = _firstList(roots, const ['resources', 'top_resources', 'resource_costs']);
    final resources = <_ResourceCost>[
      for (final item in resourceMaps)
        if (_textFromMap(item, const ['name', 'resource', 'resource_id']) case final name?)
          _ResourceCost(
            name: name,
            type: _textFromMap(item, const ['type', 'resource_type']),
            service: _textFromMap(item, const ['service', 'category']),
            usage: _textFromMap(item, const ['usage', 'usage_text', 'quantity']),
            cost: _numberFromMap(item, const ['cost_usd', 'amount_usd', 'cost']),
            change: _textFromMap(item, const ['change', 'delta', 'delta_percent']),
          ),
    ];

    return _CostModel(
      totalUsd: total,
      forecastUsd: forecast,
      budgetUsd: budget,
      savingsUsd: savings,
      nextMonthUsd: next,
      periodLabel: _firstText(roots, const ['period_label', 'billing_period', 'date_range']),
      totalDelta: _firstText(roots, const ['total_cost_delta', 'cost_delta']),
      forecastDelta: _firstText(roots, const ['forecast_delta']),
      savingsDelta: _firstText(roots, const ['savings_delta']),
      nextMonthDelta: _firstText(roots, const ['next_month_delta']),
      trend: trend,
      distribution: distribution,
      resources: resources,
      alerts: _listItems(_firstList(roots, const ['budget_alerts', 'alerts'])),
      recommendations: _listItems(_firstList(roots, const ['recommendations', 'optimization_recommendations'])),
      reports: _listItems(_firstList(roots, const ['reports', 'cost_reports'])),
    );
  }
}

class _TrendPoint {
  const _TrendPoint({required this.label, required this.value});
  final String label;
  final double value;
}

class _DistributionItem {
  const _DistributionItem({required this.label, required this.value, required this.color});
  final String label;
  final double value;
  final Color color;
}

class _ResourceCost {
  const _ResourceCost({required this.name, this.type, this.service, this.usage, this.cost, this.change});
  final String name;
  final String? type;
  final String? service;
  final String? usage;
  final double? cost;
  final String? change;
}

class _ListItem {
  const _ListItem({required this.title, this.subtitle, this.value, this.when});
  final String title;
  final String? subtitle;
  final String? value;
  final String? when;
}

List<_ListItem> _listItems(List<Map<String, Object?>> source) => [
      for (final item in source)
        if (_textFromMap(item, const ['title', 'name', 'message']) case final title?)
          _ListItem(
            title: title,
            subtitle: _textFromMap(item, const ['subtitle', 'description', 'detail']),
            value: _textFromMap(item, const ['value', 'savings', 'format']),
            when: _textFromMap(item, const ['date', 'when', 'timestamp']),
          ),
    ];

List<Map<String, Object?>> _nestedMaps(Map<String, Object?> source, List<String> keys) {
  final result = <Map<String, Object?>>[];
  for (final key in keys) {
    final value = source[key];
    if (value is Map<Object?, Object?>) {
      result.add(value.map((k, v) => MapEntry(k.toString(), v)));
    } else if (value is List<Object?>) {
      result.addAll(
        value.whereType<Map<Object?, Object?>>().map(
              (item) => item.map((k, v) => MapEntry(k.toString(), v)),
            ),
      );
    }
  }
  return result;
}

List<Map<String, Object?>> _firstList(List<Map<String, Object?>> roots, List<String> keys) {
  for (final root in roots) {
    for (final key in keys) {
      final value = root[key];
      if (value is List<Object?>) {
        return value
            .whereType<Map<Object?, Object?>>()
            .map((item) => item.map((k, v) => MapEntry(k.toString(), v)))
            .toList(growable: false);
      }
    }
  }
  return const <Map<String, Object?>>[];
}

double? _firstNumber(List<Map<String, Object?>> roots, List<String> keys) {
  for (final root in roots) {
    final value = _numberFromMap(root, keys);
    if (value != null) return value;
  }
  return null;
}

String? _firstText(List<Map<String, Object?>> roots, List<String> keys) {
  for (final root in roots) {
    final value = _textFromMap(root, keys);
    if (value != null) return value;
  }
  return null;
}

double? _numberFromMap(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is num) return value.toDouble();
    if (value is String) {
      final parsed = double.tryParse(value.replaceAll(',', '').replaceAll(r'$', '').trim());
      if (parsed != null) return parsed;
    }
  }
  return null;
}

String? _textFromMap(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value == null) continue;
    final text = value.toString().trim();
    if (text.isNotEmpty) return text;
  }
  return null;
}

String _currency(double value) {
  final negative = value < 0;
  final abs = value.abs();
  final raw = abs.toStringAsFixed(2);
  final parts = raw.split('.');
  final digits = parts.first;
  final buffer = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buffer.write(',');
    buffer.write(digits[i]);
  }
  return '${negative ? '-' : ''}\$${buffer.toString()}.${parts.last}';
}

String _copy(BuildContext context, String en, String tr) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish ? tr : en;
