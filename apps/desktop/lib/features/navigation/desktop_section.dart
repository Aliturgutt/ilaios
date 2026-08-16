import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';

enum DesktopSection {
  home('Home', Icons.home_outlined),
  goals('Goals', Icons.track_changes_outlined),
  workflows('Workflows', Icons.account_tree_outlined),
  agents('Agents', Icons.groups_2_outlined),
  liveWorkspace('Live Workspace', Icons.developer_mode_outlined),
  artifacts('Artifacts', Icons.inventory_2_outlined),
  approvals('Approvals', Icons.task_alt_outlined),
  evidence('Evidence', Icons.verified_user_outlined),
  costs('Costs', Icons.paid_outlined),
  settings('Settings', Icons.settings_outlined);

  const DesktopSection(this.label, this.icon);

  final String label;
  final IconData icon;

  String localizedLabel(BuildContext context) => context.tr('nav.$name');
}
