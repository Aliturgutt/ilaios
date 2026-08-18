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
    var successful = 0;
    var failed = 0;
    var inputTokens = 0;
    var outputTokens = 0;
    var cacheReadTokens = 0;
    var cacheWriteTokens = 0;
    var actualCost = 0.0;
    var reservedCost = 0.0;
    final latencies = <double>[];
    final providers = <String, _UsageBucket>{};
    final models = <String, _UsageBucket>{};
    final history = <UsageStatsActivity>[];

    for (final route in snapshot.runtimeRoutes) {
      final output = _map(route['output']);
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
      final cost = _firstNumber(output, route, const ['actual_cost_usd']);
      final reserved = _firstNumber(output, route, const ['reserved_cost_usd']);
      final latency = _firstNumber(output, route, const ['latency_ms']);
      final status = _firstText(output, route, const ['status', 'state', 'outcome']);
      final outcome = _terminalOutcome(status);
      final hasTokens =
          input != null || generated != null || cacheRead != null || cacheWrite != null;

      if (hasTokens) tokenCoverage++;
      if (input != null) inputCoverage++;
      if (generated != null) outputCoverage++;
      if (cacheRead != null) cacheReadCoverage++;
      if (cacheWrite != null) cacheWriteCoverage++;
      if (cost != null) costCoverage++;
      if (reserved != null) reservedCostCoverage++;
      if (latency != null) latencyCoverage++;
      if (providerId != null) providerCoverage++;
      if (modelId != null) modelCoverage++;
      if (status != null) statusCoverage++;
      if (outcome == _Outcome.success) successful++;
      if (outcome == _Outcome.failure) failed++;

      inputTokens += input ?? 0;
      outputTokens += generated ?? 0;
      cacheReadTokens += cacheRead ?? 0;
      cacheWriteTokens += cacheWrite ?? 0;
      actualCost += cost ?? 0;
      reservedCost += reserved ?? 0;
      if (latency != null) latencies.add(latency);

      void addTo(_UsageBucket bucket) => bucket.add(
            input: input,
            output: generated,
            cacheRead: cacheRead,
            cacheWrite: cacheWrite,
            cost: cost,
            latency: latency,
          );

      if (providerId != null) {
        addTo(providers.putIfAbsent(providerId, () => _UsageBucket(providerId)));
      }
      if (modelId != null) {
        final key = '${providerId ?? ''}\u001f$modelId';
        addTo(
          models.putIfAbsent(
            key,
            () => _UsageBucket(modelId, providerId: providerId),
          ),
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

    history.sort((a, b) {
      if (a.sequence != null && b.sequence != null) {
        return b.sequence!.compareTo(a.sequence!);
      }
      if (a.sequence != null) return -1;
      if (b.sequence != null) return 1;
      return 0;
    });

    final providerRows = providers.values.map((e) => e.freeze()).toList()
      ..sort(_compareBreakdown);
    final modelRows = models.values.map((e) => e.freeze()).toList()
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
      successfulRoutes: successful,
      failedRoutes: failed,
      inputTokens: inputTokens,
      outputTokens: outputTokens,
      cacheReadTokens: cacheReadTokens,
      cacheWriteTokens: cacheWriteTokens,
      observedActualCostUsd: costCoverage == 0 ? null : actualCost,
      observedReservedCostUsd: reservedCostCoverage == 0 ? null : reservedCost,
      averageLatencyMs: latencies.isEmpty
          ? null
          : latencies.reduce((a, b) => a + b) / latencies.length,
      p95LatencyMs: _p95(latencies),
      providers: List.unmodifiable(providerRows),
      models: List.unmodifiable(modelRows),
      history: List.unmodifiable(history),
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
              _summary(context, model, tr),
              const SizedBox(height: 14),
              _tokenDetail(context, model, tr),
              const SizedBox(height: 14),
              _coverage(context, model, tr),
              const SizedBox(height: 14),
              if (constraints.maxWidth >= 1000)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _breakdown(context, model.providers, tr, false)),
                    const SizedBox(width: 14),
                    Expanded(child: _breakdown(context, model.models, tr, true)),
                  ],
                )
              else ...[
                _breakdown(context, model.providers, tr, false),
                const SizedBox(height: 14),
                _breakdown(context, model.models, tr, true),
              ],
              const SizedBox(height: 14),
              _history(context, model, tr),
            ],
          ),
        ),
      ),
    );
  }

  Widget _summary(BuildContext context, UsageStatsModel model, bool tr) =>
      LayoutBuilder(
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
              _summaryCard(context, cardWidth, Icons.route_outlined,
                  tr ? 'Gözlenen rotalar' : 'Observed routes',
                  '${model.observedRoutes}',
                  tr ? 'Kalıcı runtime kayıtları' : 'Persisted runtime records'),
              _summaryCard(context, cardWidth, Icons.data_usage_outlined,
                  tr ? 'Gözlenen tokenlar' : 'Observed tokens',
                  model.observedTokens == null ? '—' : _formatInt(model.observedTokens!),
                  '${model.routesWithTokenTelemetry}/${model.observedRoutes}'),
              _summaryCard(context, cardWidth, Icons.attach_money_outlined,
                  tr ? 'Gözlenen rota maliyeti' : 'Observed route cost',
                  model.observedActualCostUsd == null
                      ? '—'
                      : _formatUsd(model.observedActualCostUsd!),
                  '${model.routesWithCostTelemetry}/${model.observedRoutes}'),
              _summaryCard(context, cardWidth, Icons.speed_outlined,
                  tr ? 'Gecikme' : 'Latency',
                  model.averageLatencyMs == null
                      ? '—'
                      : '${model.averageLatencyMs!.toStringAsFixed(0)} ms',
                  model.p95LatencyMs == null
                      ? 'p95 —'
                      : 'p95 ${model.p95LatencyMs!.toStringAsFixed(0)} ms'),
              _summaryCard(context, cardWidth, Icons.task_alt_outlined,
                  tr ? 'Gözlenen sonuçlar' : 'Observed outcomes',
                  model.observedSuccessRate == null
                      ? '—'
                      : '${model.observedSuccessRate!.toStringAsFixed(1)}%',
                  model.routesWithOutcomeTelemetry == 0
                      ? (tr ? 'Terminal sonuç kanıtı yok' : 'No terminal outcome evidence')
                      : '${model.successfulRoutes} ✓  ${model.failedRoutes} ✕  · ${model.routesWithOutcomeTelemetry}/${model.observedRoutes}'),
            ],
          );
        },
      );

  Widget _summaryCard(
    BuildContext context,
    double width,
    IconData icon,
    String label,
    String value,
    String detail,
  ) =>
      SizedBox(
        width: width,
        child: _panel(
          context,
          Row(
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
                    Text(value,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                            )),
                    Text(detail,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            )),
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  Widget _tokenDetail(BuildContext context, UsageStatsModel model, bool tr) =>
      _panel(
        context,
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _heading(context, tr ? 'Token Ayrıntısı' : 'Token Detail'),
            const SizedBox(height: 10),
            Wrap(
              spacing: 12,
              runSpacing: 10,
              children: [
                _tokenTile(context, tr ? 'Girdi' : 'Input', model.routesWithInputTokens == 0 ? null : model.inputTokens, model.routesWithInputTokens, model.observedRoutes),
                _tokenTile(context, tr ? 'Çıktı' : 'Output', model.routesWithOutputTokens == 0 ? null : model.outputTokens, model.routesWithOutputTokens, model.observedRoutes),
                _tokenTile(context, tr ? 'Cache okuma' : 'Cache read', model.routesWithCacheReadTokens == 0 ? null : model.cacheReadTokens, model.routesWithCacheReadTokens, model.observedRoutes),
                _tokenTile(context, tr ? 'Cache yazma' : 'Cache write', model.routesWithCacheWriteTokens == 0 ? null : model.cacheWriteTokens, model.routesWithCacheWriteTokens, model.observedRoutes),
              ],
            ),
          ],
        ),
      );

  Widget _tokenTile(BuildContext context, String label, int? value, int coverage, int total) =>
      Container(
        width: 190,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label),
            const SizedBox(height: 4),
            Text(value == null ? '—' : _formatInt(value),
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    )),
            Text('$coverage/$total routes',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    )),
          ],
        ),
      );

  Widget _coverage(BuildContext context, UsageStatsModel model, bool tr) =>
      _panel(
        context,
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _heading(context, tr ? 'Telemetry Kapsamı' : 'Telemetry Coverage'),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _coverageChip(context, 'Tokens', model.routesWithTokenTelemetry, model.observedRoutes),
                _coverageChip(context, 'Actual cost', model.routesWithCostTelemetry, model.observedRoutes),
                _coverageChip(context, 'Reserved cost', model.routesWithReservedCostTelemetry, model.observedRoutes),
                _coverageChip(context, 'Latency', model.routesWithLatencyTelemetry, model.observedRoutes),
                _coverageChip(context, 'Provider', model.routesWithProvider, model.observedRoutes),
                _coverageChip(context, 'Model', model.routesWithModel, model.observedRoutes),
                _coverageChip(context, 'Status', model.routesWithStatus, model.observedRoutes),
                _coverageChip(context, 'Terminal outcome', model.routesWithOutcomeTelemetry, model.observedRoutes),
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

  Widget _coverageChip(BuildContext context, String label, int observed, int total) =>
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text('$label  $observed/$total'),
      );

  Widget _breakdown(BuildContext context, List<UsageStatsBreakdown> rows, bool tr, bool models) =>
      _panel(
        context,
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _heading(context, models
                ? (tr ? 'Model Kullanımı' : 'Model Usage')
                : (tr ? 'Sağlayıcı Kullanımı' : 'Provider Usage')),
            const SizedBox(height: 8),
            if (rows.isEmpty)
              _empty(context, tr
                  ? 'Yetkili kullanım kırılımı kullanılamıyor.'
                  : 'Authoritative usage breakdown is unavailable.')
            else
              for (final row in rows.take(10))
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(row.label, maxLines: 1, overflow: TextOverflow.ellipsis),
                            if (models)
                              Text(row.providerId ?? '—',
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                                      )),
                          ],
                        ),
                      ),
                      _metric(context, tr ? 'Rota' : 'Routes', '${row.routes}'),
                      _metric(context, 'Tokens', row.tokenSamples == 0 ? '—' : _formatInt(row.observedTokens)),
                      _metric(context, tr ? 'Maliyet' : 'Cost', row.costSamples == 0 ? '—' : _formatUsd(row.observedCostUsd)),
                      _metric(context, tr ? 'Gecikme' : 'Latency', row.averageLatencyMs == null ? '—' : '${row.averageLatencyMs!.toStringAsFixed(0)} ms'),
                    ],
                  ),
                ),
          ],
        ),
      );

  Widget _history(BuildContext context, UsageStatsModel model, bool tr) =>
      _panel(
        context,
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _heading(context, tr ? 'Çalışma Geçmişi' : 'Execution History'),
            const SizedBox(height: 8),
            if (model.history.isEmpty)
              _empty(context, tr
                  ? 'Yetkili runtime çalışma geçmişi kullanılamıyor.'
                  : 'Authoritative runtime execution history is unavailable.')
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
                            Container(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              decoration: BoxDecoration(
                                border: Border(bottom: BorderSide(
                                  color: Theme.of(context).colorScheme.outlineVariant,
                                )),
                              ),
                              child: Row(
                                children: [
                                  SizedBox(width: 150, child: _oneLine(item.createdAt ?? '—')),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        _oneLine(item.agentId ?? '—'),
                                        _oneLine(item.skillId ?? item.capability ?? '—', muted: true, context: context),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  SizedBox(
                                    width: 170,
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        _oneLine(item.providerId ?? '—'),
                                        _oneLine(item.modelId ?? '—', muted: true, context: context),
                                      ],
                                    ),
                                  ),
                                  _metric(context, 'Tokens', item.observedTokens == null ? '—' : _formatInt(item.observedTokens!)),
                                  _metric(context, 'Cost', item.actualCostUsd == null ? '—' : _formatUsd(item.actualCostUsd!)),
                                  _metric(context, 'Latency', item.latencyMs == null ? '—' : '${item.latencyMs!.toStringAsFixed(0)} ms'),
                                  SizedBox(width: 90, child: _oneLine(item.status ?? '—')),
                                ],
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      );

  Widget _metric(BuildContext context, String label, String value) => SizedBox(
        width: 76,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    )),
            Text(value, maxLines: 1, overflow: TextOverflow.ellipsis),
          ],
        ),
      );

  Widget _oneLine(String value, {bool muted = false, BuildContext? context}) => Text(
        value,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: muted && context != null
            ? Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                )
            : null,
      );

  Widget _heading(BuildContext context, String text) => Text(
        text,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w800,
            ),
      );

  Widget _empty(BuildContext context, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 20),
        child: Text(text,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                )),
      );

  Widget _panel(BuildContext context, Widget child) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: child,
      );
}

class _UsageBucket {
  _UsageBucket(this.label, {this.providerId});

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
    routes++;
    if (input != null || output != null || cacheRead != null || cacheWrite != null) {
      tokenSamples++;
    }
    inputTokens += input ?? 0;
    outputTokens += output ?? 0;
    cacheReadTokens += cacheRead ?? 0;
    cacheWriteTokens += cacheWrite ?? 0;
    if (cost != null) {
      costSamples++;
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
  if (const {'completed', 'complete', 'success', 'succeeded', 'ok'}.contains(normalized)) {
    return _Outcome.success;
  }
  if (const {'failed', 'failure', 'error'}.contains(normalized)) {
    return _Outcome.failure;
  }
  return null;
}

int _compareBreakdown(UsageStatsBreakdown a, UsageStatsBreakdown b) {
  final routes = b.routes.compareTo(a.routes);
  return routes != 0 ? routes : a.label.compareTo(b.label);
}

Map<String, Object?> _map(Object? value) {
  if (value is Map<Object?, Object?>) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return const {};
}

String? _firstText(Map<String, Object?> primary, Map<String, Object?> fallback, List<String> keys) {
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

int? _firstInt(Map<String, Object?> primary, Map<String, Object?> fallback, List<String> keys) {
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

double? _firstNumber(Map<String, Object?> primary, Map<String, Object?> fallback, List<String> keys) {
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
  if (value is double && value.isFinite && value >= 0 && value == value.truncateToDouble()) {
    return value.toInt();
  }
  if (value is String) {
    final parsed = int.tryParse(value.trim());
    if (parsed != null && parsed >= 0) return parsed;
  }
  return null;
}

double? _number(Object? value) {
  final parsed = value is num
      ? value.toDouble()
      : value is String
          ? double.tryParse(value.trim())
          : null;
  return parsed != null && parsed.isFinite && parsed >= 0 ? parsed : null;
}

double? _p95(List<double> values) {
  if (values.isEmpty) return null;
  final sorted = List<double>.of(values)..sort();
  final index = (sorted.length * .95).ceil() - 1;
  return sorted[index < 0 ? 0 : index];
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
