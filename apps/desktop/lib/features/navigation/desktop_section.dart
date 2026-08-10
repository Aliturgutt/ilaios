import 'package:flutter/material.dart';

enum DesktopSection {
  controlCenter('Control Center', Icons.dashboard_outlined, true),
  liveExecution('Live Execution', Icons.play_circle_outline, false),
  workflows('Workflows', Icons.account_tree_outlined, false),
  agents('Agents', Icons.smart_toy_outlined, false),
  evidence('Evidence', Icons.fact_check_outlined, false),
  approvals('Approvals', Icons.admin_panel_settings_outlined, false);

  const DesktopSection(this.label, this.icon, this.capabilityConnected);

  final String label;
  final IconData icon;
  final bool capabilityConnected;
}
