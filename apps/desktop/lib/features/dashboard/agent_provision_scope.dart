import 'package:flutter/widgets.dart';

/// Carries the authenticated canonical-agent provisioning callback through the
/// reference shell without widening the V10 surface API further.
class AgentProvisionScope extends InheritedWidget {
  const AgentProvisionScope({
    required this.onProvisionAgent,
    required super.child,
    super.key,
  });

  final Future<void> Function(String agentId)? onProvisionAgent;

  static AgentProvisionScope? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AgentProvisionScope>();

  @override
  bool updateShouldNotify(AgentProvisionScope oldWidget) =>
      oldWidget.onProvisionAgent != onProvisionAgent;
}
