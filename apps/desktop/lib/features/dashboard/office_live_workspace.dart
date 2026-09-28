import 'package:flutter/material.dart';
import 'office_team_counts.dart';

/// Shows only the approved reference image. Verified runtime counters remain
/// available to the surrounding Agents page; no counters cover the artwork.
class OfficeLiveWorkspace extends StatelessWidget {
  const OfficeLiveWorkspace({required this.counts, super.key});
  final Map<String, OfficeTeamCounts> counts;

  @override
  Widget build(BuildContext context) => Center(
    child: Image.asset(
      'assets/pixel_agents/workspace/office_reference.png',
      fit: BoxFit.contain,
      filterQuality: FilterQuality.none,
    ),
  );
}
