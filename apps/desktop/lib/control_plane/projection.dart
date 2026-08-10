import 'package:flutter/foundation.dart';

@immutable
class ControlPlaneProjection {
  const ControlPlaneProjection({
    required this.connected,
    required this.status,
    required this.goalCount,
    required this.jobCount,
    required this.lastEvent,
    this.schemaVersion,
  });

  const ControlPlaneProjection.unavailable({
    this.status = 'Authoritative control plane unavailable',
  }) : connected = false,
       goalCount = null,
       jobCount = null,
       lastEvent = null,
       schemaVersion = null;

  final bool connected;
  final String status;
  final int? goalCount;
  final int? jobCount;
  final String? lastEvent;
  final String? schemaVersion;
}
