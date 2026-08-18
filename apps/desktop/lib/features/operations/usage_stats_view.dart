import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';

@immutable
class UsageStatsBreakdown {
  const UsageStatsBreakdown({
    required this.label,
    required this.routes,
    required this.inputTokens,
    required this.outputTokens,
    required this.cacheReadTokens,
    required this.cacheWriteTokens,
    required this.tokenSamples,
    required this.observedCostUsd,
    required this.costSamples,
    required this.averageLatencyMs,
    this.providerId,
  });

  final String label;
  final String? providerId;
  final int routes;
  final int inputTokens;
  final int outputTokens;
  final int cacheReadTokens;
  final int cacheWriteTokens;
  final int tokenSamples;
  final double observedCostUsd;
  final int costSamples;
  final double? averageLatencyMs;

  int get observedTokens =>
      inputTokens + outputTokens + cacheReadTokens + cacheWriteTokens;
}

@immutable
class UsageStatsActivity {
  const UsageStatsActivity({
    required this.sequence,
    required this.createdAt,
    required this.agentId,
    required this.skillId,
    required this.capability,
    required this.providerId,
    required this.modelId,
    required this.inputTokens,
    required this.outputTokens,
    required this.cacheReadTokens,
    required this.cacheWriteTokens,
    required this.actualCostUsd,
    required this.latencyMs,
    required this.status,
  });

  final int? sequence;
  final String? createdAt;
  final String? agentId;
  final String? skillId;
  final String? capability;
  final String? providerId;
  final String? modelId;
  final int? inputTokens;
  final int? outputTokens;
  final int? cacheReadTokens;
  final int? cacheWriteTokens;
  final double? actualCostUsd;
  final double? latencyMs;
  final String? status;

  bool get hasTokenTelemetry =>
      inputTokens != null ||
      outputTokens != null ||
      cacheReadTokens != null ||
      cacheWriteTokens != null;

  int? get observedTokens => hasTokenTelemetry
      ? (inputTokens ?? 0) +
          (outputTokens ?? 0) +
          (cacheReadTokens ?? 0) +
          (cacheWriteTokens ?? 0)
      : null;
}

@immutable
class UsageStatsModel {
  const UsageStatsModel({
    required this.observedRoutes,
    required this.routesWithTokenTelemetry,
    required this.routesWithInputTokens,
    required this.routesWithOutputTokens,
    required this.routesWithCacheReadTokens,
    required this.routesWithCacheWriteTokens,
    required this.routesWithCostTelemetry,
    required this.routesWithReservedCostTelemetry,
    required this.routesWithLatencyTelemetry,
    required this.routesWithProvider,
    required this.routesWithModel,
    required this.routesWithStatus,
    required this.successfulRoutes,
    required this.failedRoutes,
    required this.inputTokens,
    required this.outputTokens,
    required this.cacheReadTokens,
    required this.cacheWriteTokens,
    required this.observedActualCostUsd,
    required this.observedReservedCostUsd,
    required this.averageLatencyMs,
    required this.p95LatencyMs,
    required this.providers,
    required this.models,
    required this.history,
  });

  final int observedRoutes;
  final int routesWithTokenTelemetry;
  final int routesWithInputTokens;
  final int routesWithOutputTokens;
  final int routesWithCacheReadTokens;
  final int routesWithCacheWriteTokens;
  final int routesWithCostTelemetry;
  final int routesWithReservedCostTelemetry;
  final int routesWithLatencyTelemetry;
  final int routesWithProvider;
  final int routesWithModel;
  final int routesWithStatus;
  final int successfulRoutes;
  final int failedRoutes;
  final int inputTokens;
  final int outputTokens;
  final int cacheReadTokens;
  final int cacheWriteTokens;
  final double? observedActualCostUsd;
  final double? observedReservedCostUsd;
  final double? averageLatencyMs;
  final double? p95LatencyMs;
  final List<UsageStatsBreakdown> providers;
  final List<UsageStatsBreakdown> models;
  final List<UsageStatsActivity> history;

  int? get observedTokens => routesWithTokenTelemetry == 0
      ? null
      : inputTokens + outputTokens + cacheReadTokens + cacheWriteTokens;

  int get routesWithOutcomeTelemetry => successfulRoutes + failedRoutes;

  double? get observedSuccessRate => routesWithOutcomeTelemetry == 0
      ? null
      : successfulRoutes / routesWithOutcomeTelemetry * 100;

  factory UsageStatsModel.fromSnapshot(OperationalSnapshot snapshot) {
    var tokenCoverage = 0;
    var inputCoverage = 0;
    var outputCoverage = 0;
    var cacheReadCoverage = 0;
    var cacheWriteCoverage = 0;
    var costCoverage = 0;
    var reservedCostCoverage = 0;
    var latencyCoverage = 0;
    var providerCoverage = 0;
    var modelCoverage = 0;
    var statusCoverage = 0;
    var successfulRoutes = 0;
    var failedRoutes = 0;
    var inputTokens = 0;
    var outputTokens = 0;
    var cacheReadTokens = 0;
    var cacheWriteTokens = 0;
    var actualCost = 0.0;
    var reservedCost = 0.0;
    final latencies = <double>[];
    final providerBuckets = <String, _MutableUsageBucket>{};
    final modelBuckets = <String, _MutableUsageBucket>{};
    final history = <UsageStatsActivity>[];

    for (final route in snapshot.runtimeRoutes) {
      final output = _asMap(route['output']);
      final providerId = _firstText(output, route, const ['provider_id']);
      final modelId = _firstText(output, route, const ['model_id']);
      final input = _firstInt(output, route, const ['input_tokens']);
      final generated = _firstInt(output, route, const ['output_tokens']);
      final cacheRead = _firstInt(
        output,
        route,
        const ['cache_read_tokens', 'cached_input_tokens', 'input_cached_tokens'],
      );
      final cacheWrite = _firstInt(
        output,
        route,
        const ['cache_write_tokens', 'cached_output_tokens'],
      );
      final hasTokens =
          input != null || generated != null || cacheRead != null || cacheWrite != null;
      final cost = _firstNumber(output, route, const ['actual_cost_usd']);
      final reserved = _firstNumber(output, route, const ['reserved_cost_usd']);
      final latency = _firstNumber(output, route, const ['latency_ms']);
      final status = _firstText(output, route, const ['status', 'state', 'outcome']);
      final outcome = _terminalOutcome(status);

      if (hasTokens) tokenCoverage += 1;
      if (input != null) inputCoverage += 1;
      if (generated != null) outputCoverage += 1;
      if (cacheRead != null) cacheReadCoverage += 1;
      if (cacheWrite != null) cacheWriteCoverage += 1;
      if (cost != null) costCoverage += 1;
      if (reserved != null) reservedCostCoverage += 1;
      if (latency != null) latencyCoverage += 1;
      if (providerId != null) providerCoverage += 1;
      if (modelId != null) modelCoverage += 1;
      if (status != null) statusCoverage += 1;
      if (outcome == _Outcome.success) successfulRoutes += 1;
      if (outcome == _Outcome.failure) failedRoutes += 1;

      inputTokens += input ?? 0;
      outputTokens += generated ?? 0;
      cacheReadTokens += cacheRead ?? 0;
      cacheWriteTokens += cacheWrite ?? 0;
      actualCost += cost ?? 0;
      reservedCost += reserved ?? 0;
      if (latency != null) latencies.add(latency);

      if (providerId != null) {
        providerBuckets
            .putIfAbsent(providerId, () => _MutableUsageBucket(providerId))
            .add(
              input: input,
              output: generated,
              cacheRead: cacheRead,
              cacheWrite: cacheWrite,
              cost: cost,
              latency: latency,
            );
      }
      if (modelId != null) {
        final modelKey = '${providerId ?? ''}\u001f$modelId';
        modelBuckets
            .putIfAbsent(
              modelKey,
              () => _MutableUsageBucket(modelId, providerId: providerId),
            )
            .add(
              input: input,
              output: generated,
              cacheRead: cacheRead,
              cacheWrite: cacheWrite,
              cost: cost,
              latency: latency,
            );
      }

      history.add(
        UsageStatsActivity(
          sequence: _int(route['sequence']),
          createdAt: _text(route['created_at']),
          agentId: _text(route['agent_id']),
          skillId: _text(route['skill_id']),
          capability: _text(route['capability']),
          providerId: providerId,
          modelId: modelId,
          inputTokens: input,
          outputTokens: generated,
          cacheReadTokens: cacheRead,
          cacheWriteTokens: cacheWrite,
          actualCostUsd: cost,
          latencyMs: latency,
          status: status,
        ),
      );
    }

    history.sort((left, right) {
      final a = left.sequence;
      final b = right.sequence;
      if (a != null && b != null) return b.compareTo(a);
      if (a != null) return -1;
      if (b != null) return 1;
      return 0;
    });

    final providerRows = providerBuckets.values
        .map((bucket) => bucket.freeze())
        .toList(growable: false)
      ..sort(_compareBreakdown);
    final modelRows = modelBuckets.values
        .map((bucket) => bucket.freeze())
        .toList(growable: false)
      ..sort(_compareBreakdown);

    return UsageStatsModel(
      observedRoutes: snapshot.runtimeRoutes.length,
      routesWithTokenTelemetry: tokenCoverage,
      routesWithInputTokens: inputCoverage,
      routesWithOutputTokens: outputCoverage,
      routesWithCacheReadTokens: cacheReadCoverage,
      routesWithCacheWriteTokens: cacheWriteCoverage,
      routesWithCostTelemetry: costCoverage,
      routesWithReservedCostTelemetry: reservedCostCoverage,
      routesWithLatencyTelemetry: latencyCoverage,
      routesWithProvider: providerCoverage,
      routesWithModel: modelCoverage,
      routesWithStatus: statusCoverage,
      successfulRoutes: successfulRoutes,
      failedRoutes: failedRoutes,
      inputTokens: inputTokens,
      outputTokens: outputTokens,
      cacheReadTokens: cacheReadTokens,
      cacheWriteTokens: cacheWriteTokens,
      observedActualCostUsd: costCoverage == 0 ? null : actualCost,
      observedReservedCostUsd:
          reservedCostCoverage == 0 ? null : reservedCost,
      averageLatencyMs: latencies.isEmpty
          ? null
          : latencies.reduce((a, b) => a + b) / latencies.length,
      p95LatencyMs: _percentile95(latencies),
      providers: List<UsageStatsBreakdown>.unmodifiable(providerRows),
      models: List<UsageStatsBreakdown>.unmodifiable(modelRows),
      history: List<UsageStatsActivity>.unmodifiable(history),
    );
  }
}

class UsageStatsView extends StatelessWidget {
  const UsageStatsView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  Widget build(BuildContext context) {
    final model = UsageStatsModel.fromSnapshot(snapshot);
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    final scheme = Theme.of(context).colorScheme;
    return Container(
      key: const Key('usage-stats-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      child: LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(22, 18, 22, 84),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                tr ? 'Kullanım ve İstatistikler' : 'Usage & Stats',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 5),
              Text(
                tr
                    ? 'Mevcut kimliği doğrulanmış control-plane runtime-route projeksiyonundan türetilen gözlenmiş kullanım, maliyet ve çalışma geçmişi.'
                    : 'Observed usage, cost and execution history derived from the current authenticated control-plane runtime-route projection.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 16),
              _SummaryGrid(model: model, tr: tr),
              const SizedBox(height: 14),
              _TokenDetailPanel(model: model, tr: tr),
              const SizedBox(height: 14),
              _CoveragePanel(model: model, tr: tr, status: status),
              const SizedBox(height: 14),
              if (constraints.maxWidth >= 1000)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: _BreakdownPanel(
                        title: tr ? 'Sağlayıcı Kullanımı' : 'Provider Usage',
                        rows: model.providers,
                        tr: tr,
                        showProvider: false,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: _BreakdownPanel(
                        title: tr ? 'Model Kullanımı' : 'Model Usage',
                        rows: model.models,
                        tr: tr,
                        showProvider: true,
                      ),
                    ),
                  ],
                )
              else ...[
                _BreakdownPanel(
                  title: tr ? 'Sağlayıcı Kullanımı' : 'Provider Usage',
                  rows: model.providers,
                  tr: tr,
                  showProvider: false,
                ),
                const SizedBox(height: 14),
                _BreakdownPanel(
                  title: tr ? 'Model Kullanımı' : 'Model Usage',
                  rows: model.models,
                  tr: tr,
                  showProvider: true,
                ),
              ],
              const SizedBox(height: 14),
              _HistoryPanel(model: model, tr: tr),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryGrid extends StatelessWidget {
  const _SummaryGrid({required this.model, required this.tr});

  final UsageStatsModel model;
  final bool tr;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final cardWidth = width >= 1050
              ? (width - 42) / 4
              : width >= 600
                  ? (width - 14) / 2
                  : width;
          return Wrap(
            spacing: 14,
            runSpacing: 14,
            children: [
              _SummaryCard(
                width: cardWidth,
                icon: Icons.route_outlined,
                label: tr ? 'Gözlenen rotalar' : 'Observed routes',
                value: model.observedRoutes.toString(),
                detail: tr ? 'Kalıcı runtime kayıtları' : 'Persisted runtime records',
              ),
              _SummaryCard(
                width: cardWidth,
                icon: Icons.data_usage_outlined,
                label: tr ? 'Gözlenen tokenlar' : 'Observed tokens',
                value: model.observedTokens == null
                    ? '—'
                    : _formatInt(model.observedTokens!),
                detail: '${model.routesWithTokenTelemetry}/${model.observedRoutes}',
              ),
              _SummaryCard(
                width: cardWidth,
                icon: Icons.attach_money_outlined,
                label: tr ? 'Gözlenen rota maliyeti' : 'Observed route cost',
                value: model.observedActualCostUsd == null
                    ? '—'
                    : _formatUsd(model.observedActualCostUsd!),
                detail: '${model.routesWithCostTelemetry}/${model.observedRoutes}',
              ),
              _SummaryCard(
                width: cardWidth,
                icon: Icons.speed_outlined,
                label: tr ? 'Gecikme' : 'Latency',
                value: model.averageLatencyMs == null
                    ? '—'
                    : '${model.averageLatencyMs!.toStringAsFixed(0)} ms',
                detail: model.p95LatencyMs == null
                    ? 'p95 —'
                    : 'p95 ${model.p95LatencyMs!.toStringAsFixed(0)} ms',
              ),
              _SummaryCard(
                width: cardWidth,
                icon: Icons.task_alt_outlined,
                label: tr ? 'Gözlenen sonuçlar' : 'Observed outcomes',
                value: model.observedSuccessRate == null
                    ? '—'
                    : '${model.observedSuccessRate!.toStringAsFixed(1)}%',
                detail: model.routesWithOutcomeTelemetry == 0
                    ? (tr ? 'Terminal sonuç kanıtı yok' : 'No terminal outcome evidence')
                    : '${model.successfulRoutes} ✓  ${model.failedRoutes} ✕  · ${model.routesWithOutcomeTelemetry}/${model.observedRoutes}',
              ),
            ],
          );
        },
      );
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.width,
    required this.icon,
    required this.label,
    required this.value,
    required this.detail,
  });

  final double width;
  final IconData icon;
  final String label;
  final String value;
  final String detail;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: width,
        child: _Panel(
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: IlaiosTheme.enterpriseCyan.withValues(alpha: .12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: IlaiosTheme.enterpriseCyan, size: 21),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 4),
                    Text(
                      value,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      detail,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}

class _TokenDetailPanel extends StatelessWidget {
  const _TokenDetailPanel({required this.model, required this.tr});

  final UsageStatsModel model;
  final bool tr;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              tr ? 'Token Ayrıntısı' : 'Token Detail',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 12,
              runSpacing: 10,
              children: [
                _TokenMetric(
                  label: tr ? 'Girdi' : 'Input',
                  value: model.routesWithInputTokens == 0
                      ? null
                      : model.inputTokens,
                  coverage: model.routesWithInputTokens,
                  total: model.observedRoutes,
                ),
                _TokenMetric(
                  label: tr ? 'Çıktı' : 'Output',
                  value: model.routesWithOutputTokens == 0
                      ? null
                      : model.outputTokens,
                  coverage: model.routesWithOutputTokens,
                  total: model.observedRoutes,
                ),
                _TokenMetric(
                  label: tr ? 'Cache okuma' : 'Cache read',
                  value: model.routesWithCacheReadTokens == 0
                      ? null
                      : model.cacheReadTokens,
                  coverage: model.routesWithCacheReadTokens,
                  total: model.observedRoutes,
                ),
                _TokenMetric(
                  label: tr ? 'Cache yazma' : 'Cache write',
                  value: model.routesWithCacheWriteTokens == 0
                      ? null
                      : model.cacheWriteTokens,
                  coverage: model.routesWithCacheWriteTokens,
                  total: model.observedRoutes,
                ),
              ],
            ),
          ],
        ),
      );
}

class _TokenMetric extends StatelessWidget {
  const _TokenMetric({
    required this.label,
    required this.value,
    required this.coverage,
    required this.total,
  });

  final String label;
  final int? value;
  final int coverage;
  final int total;

  @override
  Widget build(BuildContext context) => Container(
        width: 190,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(height: 4),
            Text(
              value == null ? '—' : _formatInt(value!),
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            Text(
              '$coverage/$total routes',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      );
}

class _CoveragePanel extends StatelessWidget {
  const _CoveragePanel({
    required this.model,
    required this.tr,
    required this.status,
  });

  final UsageStatsModel model;
  final bool tr;
  final String status;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              tr ? 'Telemetry Kapsamı' : 'Telemetry Coverage',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _CoverageChip('Tokens', model.routesWithTokenTelemetry, model.observedRoutes),
                _CoverageChip('Actual cost', model.routesWithCostTelemetry, model.observedRoutes),
                _CoverageChip('Reserved cost', model.routesWithReservedCostTelemetry, model.observedRoutes),
                _CoverageChip('Latency', model.routesWithLatencyTelemetry, model.observedRoutes),
                _CoverageChip('Provider', model.routesWithProvider, model.observedRoutes),
                _CoverageChip('Model', model.routesWithModel, model.observedRoutes),
                _CoverageChip('Status', model.routesWithStatus, model.observedRoutes),
                _CoverageChip('Terminal outcome', model.routesWithOutcomeTelemetry, model.observedRoutes),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              model.observedRoutes == 0
                  ? (tr
                      ? 'Yetkili runtime-route telemetrisi kullanılamıyor. Sentetik token, maliyet, sağlayıcı, model, gecikme veya başarı oranı üretilmez. Runtime durumu: $status'
                      : 'Authoritative runtime-route telemetry is unavailable. No synthetic token, cost, provider, model, latency or success-rate values are generated. Runtime status: $status')
                  : (tr
                      ? 'Eksik alanlar “—” olarak kalır. Başarı oranı yalnızca açık terminal success/failure durumlarından hesaplanır; eksik maliyet veya token verisi tahmin edilmez.'
                      : 'Missing fields remain “—”. Success rate uses explicit terminal success/failure states only; missing cost or token data is never estimated.'),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      );
}

class _CoverageChip extends StatelessWidget {
  const _CoverageChip(this.label, this.observed, this.total);

  final String label;
  final int observed;
  final int total;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text('$label  $observed/$total'),
      );
}

class _BreakdownPanel extends StatelessWidget {
  const _BreakdownPanel({
    required this.title,
    required this.rows,
    required this.tr,
    required this.showProvider,
  });

  final String title;
  final List<UsageStatsBreakdown> rows;
  final bool tr;
  final bool showProvider;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            if (rows.isEmpty)
              _EmptyText(
                tr ? 'Yetkili kullanım kırılımı kullanılamıyor.' : 'Authoritative usage breakdown is unavailable.',
              )
            else
              for (final row in rows.take(10))
                _BreakdownRow(row: row, showProvider: showProvider, tr: tr),
          ],
        ),
      );
}

class _BreakdownRow extends StatelessWidget {
  const _BreakdownRow({
    required this.row,
    required this.showProvider,
    required this.tr,
  });

  final UsageStatsBreakdown row;
  final bool showProvider;
  final bool tr;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(row.label, maxLines: 1, overflow: TextOverflow.ellipsis),
                  if (showProvider)
                    Text(
                      row.providerId ?? '—',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            _MetricText(tr ? 'Rota' : 'Routes', row.routes.toString()),
            const SizedBox(width: 8),
            _MetricText(
              'Tokens',
              row.tokenSamples == 0 ? '—' : _formatInt(row.observedTokens),
            ),
            const SizedBox(width: 8),
            _MetricText(
              tr ? 'Maliyet' : 'Cost',
              row.costSamples == 0 ? '—' : _formatUsd(row.observedCostUsd),
            ),
            const SizedBox(width: 8),
            _MetricText(
              tr ? 'Gecikme' : 'Latency',
              row.averageLatencyMs == null
                  ? '—'
                  : '${row.averageLatencyMs!.toStringAsFixed(0)} ms',
            ),
          ],
        ),
      );
}

class _MetricText extends StatelessWidget {
  const _MetricText(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 76,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            Text(value, maxLines: 1, overflow: TextOverflow.ellipsis),
          ],
        ),
      );
}

class _HistoryPanel extends StatelessWidget {
  const _HistoryPanel({required this.model, required this.tr});

  final UsageStatsModel model;
  final bool tr;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              tr ? 'Çalışma Geçmişi' : 'Execution History',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            if (model.history.isEmpty)
              _EmptyText(
                tr ? 'Yetkili runtime çalışma geçmişi kullanılamıyor.' : 'Authoritative runtime execution history is unavailable.',
              )
            else
              LayoutBuilder(
                builder: (context, constraints) {
                  final contentWidth = constraints.maxWidth < 980
                      ? 980.0
                      : constraints.maxWidth;
                  return SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: SizedBox(
                      width: contentWidth,
                      child: Column(
                        children: [
                          for (final item in model.history.take(20))
                            _HistoryRow(item: item),
                        ],
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      );
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.item});

  final UsageStatsActivity item;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
          ),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 150,
              child: Text(item.createdAt ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.agentId ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis),
                  Text(
                    item.skillId ?? item.capability ?? '—',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            SizedBox(
              width: 170,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.providerId ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis),
                  Text(
                    item.modelId ?? '—',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            _MetricText('Tokens', item.observedTokens == null ? '—' : _formatInt(item.observedTokens!)),
            const SizedBox(width: 8),
            _MetricText('Cost', item.actualCostUsd == null ? '—' : _formatUsd(item.actualCostUsd!)),
            const SizedBox(width: 8),
            _MetricText('Latency', item.latencyMs == null ? '—' : '${item.latencyMs!.toStringAsFixed(0)} ms'),
            const SizedBox(width: 10),
            SizedBox(
              width: 90,
              child: Text(item.status ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
          ],
        ),
      );
}

class _EmptyText extends StatelessWidget {
  const _EmptyText(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 20),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
      );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: child,
      );
}

class _MutableUsageBucket {
  _MutableUsageBucket(this.label, {this.providerId});

  final String label;
  final String? providerId;
  var routes = 0;
  var inputTokens = 0;
  var outputTokens = 0;
  var cacheReadTokens = 0;
  var cacheWriteTokens = 0;
  var tokenSamples = 0;
  var observedCostUsd = 0.0;
  var costSamples = 0;
  final latencies = <double>[];

  void add({
    required int? input,
    required int? output,
    required int? cacheRead,
    required int? cacheWrite,
    required double? cost,
    required double? latency,
  }) {
    routes += 1;
    if (input != null || output != null || cacheRead != null || cacheWrite != null) {
      tokenSamples += 1;
    }
    inputTokens += input ?? 0;
    outputTokens += output ?? 0;
    cacheReadTokens += cacheRead ?? 0;
    cacheWriteTokens += cacheWrite ?? 0;
    if (cost != null) {
      costSamples += 1;
      observedCostUsd += cost;
    }
    if (latency != null) latencies.add(latency);
  }

  UsageStatsBreakdown freeze() => UsageStatsBreakdown(
        label: label,
        providerId: providerId,
        routes: routes,
        inputTokens: inputTokens,
        outputTokens: outputTokens,
        cacheReadTokens: cacheReadTokens,
        cacheWriteTokens: cacheWriteTokens,
        tokenSamples: tokenSamples,
        observedCostUsd: observedCostUsd,
        costSamples: costSamples,
        averageLatencyMs: latencies.isEmpty
            ? null
            : latencies.reduce((a, b) => a + b) / latencies.length,
      );
}

enum _Outcome { success, failure }

_Outcome? _terminalOutcome(String? status) {
  final normalized = status?.trim().toLowerCase();
  if (normalized == null || normalized.isEmpty) return null;
  if (const {'completed', 'complete', 'success', 'succeeded', 'ok'}
      .contains(normalized)) {
    return _Outcome.success;
  }
  if (const {'failed', 'failure', 'error'}.contains(normalized)) {
    return _Outcome.failure;
  }
  return null;
}

int _compareBreakdown(UsageStatsBreakdown left, UsageStatsBreakdown right) {
  final byRoutes = right.routes.compareTo(left.routes);
  return byRoutes != 0 ? byRoutes : left.label.compareTo(right.label);
}

Map<String, Object?> _asMap(Object? value) {
  if (value is Map<Object?, Object?>) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return const <String, Object?>{};
}

String? _firstText(
  Map<String, Object?> primary,
  Map<String, Object?> fallback,
  List<String> keys,
) {
  for (final key in keys) {
    final value = _text(primary[key]);
    if (value != null) return value;
  }
  for (final key in keys) {
    final value = _text(fallback[key]);
    if (value != null) return value;
  }
  return null;
}

int? _firstInt(
  Map<String, Object?> primary,
  Map<String, Object?> fallback,
  List<String> keys,
) {
  for (final key in keys) {
    final value = _int(primary[key]);
    if (value != null) return value;
  }
  for (final key in keys) {
    final value = _int(fallback[key]);
    if (value != null) return value;
  }
  return null;
}

double? _firstNumber(
  Map<String, Object?> primary,
  Map<String, Object?> fallback,
  List<String> keys,
) {
  for (final key in keys) {
    final value = _number(primary[key]);
    if (value != null) return value;
  }
  for (final key in keys) {
    final value = _number(fallback[key]);
    if (value != null) return value;
  }
  return null;
}

String? _text(Object? value) {
  if (value is! String) return null;
  final normalized = value.trim();
  return normalized.isEmpty ? null : normalized;
}

int? _int(Object? value) {
  if (value is int && value >= 0) return value;
  if (value is double &&
      value.isFinite &&
      value >= 0 &&
      value == value.truncateToDouble()) {
    return value.toInt();
  }
  if (value is String) {
    final parsed = int.tryParse(value.trim());
    if (parsed != null && parsed >= 0) return parsed;
  }
  return null;
}

double? _number(Object? value) {
  if (value is num) {
    final parsed = value.toDouble();
    if (parsed.isFinite && parsed >= 0) return parsed;
  }
  if (value is String) {
    final parsed = double.tryParse(value.trim());
    if (parsed != null && parsed.isFinite && parsed >= 0) return parsed;
  }
  return null;
}

double? _percentile95(List<double> values) {
  if (values.isEmpty) return null;
  final sorted = List<double>.of(values)..sort();
  final rawIndex = (sorted.length * .95).ceil() - 1;
  final index = rawIndex < 0 ? 0 : rawIndex;
  return sorted[index];
}

String _formatInt(int value) {
  final text = value.toString();
  final output = StringBuffer();
  for (var i = 0; i < text.length; i++) {
    if (i > 0 && (text.length - i) % 3 == 0) output.write(',');
    output.write(text[i]);
  }
  return output.toString();
}

String _formatUsd(double value) {
  final digits = value.abs() < 1 ? 4 : 2;
  return '\$${value.toStringAsFixed(digits)}';
}
