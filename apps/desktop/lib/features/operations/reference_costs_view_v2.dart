import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import 'reference_costs_view.dart';

/// Viewport-hardened entry point for the approved Costs reference surface.
///
/// Keeps the page in one desktop viewport at compact Windows/DPI sizes while
/// preserving the same visual hierarchy. The underlying Costs view remains
/// authority-only: reference screenshot telemetry is never synthesized.
class ReferenceCostsViewV2 extends StatelessWidget {
  const ReferenceCostsViewV2({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);

    Widget canvas(double width, double height) => MediaQuery(
          data: media.copyWith(textScaler: const TextScaler.linear(.84)),
          child: SizedBox(
            width: width,
            height: height,
            child: ReferenceCostsView(snapshot: snapshot, status: status),
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
