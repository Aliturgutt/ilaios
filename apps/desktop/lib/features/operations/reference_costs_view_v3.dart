import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../services/cost_export_service.dart';
import 'reference_costs_view.dart';

/// Interactive entry point for the approved Costs surface.
///
/// The reference view remains presentation-only and authority-derived. This
/// wrapper adds the real Export action without copying screenshot telemetry or
/// moving file-system concerns into the visual model.
class ReferenceCostsViewV3 extends StatelessWidget {
  const ReferenceCostsViewV3({
    required this.snapshot,
    required this.status,
    this.onExport,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final Future<String> Function(OperationalSnapshot snapshot)? onExport;

  Future<void> _export(BuildContext context) async {
    final export = onExport ?? CostExportService.export;
    try {
      final path = await export(snapshot);
      if (!context.mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(
          content: Text(
            Localizations.localeOf(context).languageCode == 'tr'
                ? 'Maliyet raporu kaydedildi: $path'
                : 'Cost report saved: $path',
          ),
        ),
      );
    } on CostExportException catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);

    Widget canvas(double width, double height) => MediaQuery(
          data: media.copyWith(textScaler: const TextScaler.linear(.84)),
          child: SizedBox(
            width: width,
            height: height,
            child: Stack(
              children: [
                Positioned.fill(
                  child: ReferenceCostsView(
                    snapshot: snapshot,
                    status: status,
                  ),
                ),
                Positioned(
                  top: 13,
                  right: 18,
                  child: Semantics(
                    button: true,
                    enabled: CostExportService.canExport(snapshot),
                    label: Localizations.localeOf(context).languageCode == 'tr'
                        ? 'Maliyet raporunu dışa aktar'
                        : 'Export cost report',
                    child: Tooltip(
                      message: Localizations.localeOf(context).languageCode == 'tr'
                          ? 'Gerçek maliyet telemetrisini dışa aktar'
                          : 'Export authoritative cost telemetry',
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          key: const Key('costs-export-action'),
                          onTap: CostExportService.canExport(snapshot)
                              ? () => _export(context)
                              : null,
                          borderRadius: BorderRadius.circular(7),
                          child: const SizedBox(width: 100, height: 33),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );

    return LayoutBuilder(
      builder: (context, constraints) {
        const minWidth = 1180.0;
        const minHeight = 760.0;
        final designWidth = math.max(minWidth, constraints.maxWidth);
        final designHeight = math.max(minHeight, constraints.maxHeight);
        if (constraints.maxWidth >= minWidth && constraints.maxHeight >= minHeight) {
          return canvas(constraints.maxWidth, constraints.maxHeight);
        }
        return ClipRect(
          key: const Key('reference-costs-scaled-viewport'),
          child: SizedBox.expand(
            child: FittedBox(
              fit: BoxFit.contain,
              alignment: Alignment.topLeft,
              child: canvas(designWidth, designHeight),
            ),
          ),
        );
      },
    );
  }
}
