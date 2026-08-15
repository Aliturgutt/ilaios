import 'package:flutter/material.dart';

enum DesktopSection {
  create('Create', Icons.auto_awesome_outlined),
  controlCenter('Control Center', Icons.dashboard_outlined),
  liveExecution('Live Execution', Icons.play_circle_outline),
  deliveries('Deliveries', Icons.inventory_2_outlined),
  evidence('Evidence', Icons.fact_check_outlined),
  governance('Governance', Icons.admin_panel_settings_outlined);

  const DesktopSection(this.label, this.icon);

  final String label;
  final IconData icon;
}
