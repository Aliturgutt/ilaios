import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/dashboard/agent_runtime_status.dart';
import 'package:ilaios_desktop/features/dashboard/office_team_counts.dart';

void main() {
  test('offline agents do not become working or idle', () {
    final counts = countVerifiedOfficeTeams(
      {
        'a': AgentRuntimeDisplayState.offline,
        'b': AgentRuntimeDisplayState.offline,
      },
      {'a': 'security', 'b': 'web'},
    );
    expect(counts['security']!.registered, 1);
    expect(counts['security']!.working, 0);
    expect(counts['web']!.working, 0);
    expect(counts['core']!.registered, 0);
  });
  test('only canonical team records contribute to each team', () {
    final counts = countVerifiedOfficeTeams(
      {
        'a': AgentRuntimeDisplayState.working,
        'b': AgentRuntimeDisplayState.waiting,
        'c': AgentRuntimeDisplayState.idle,
        'd': AgentRuntimeDisplayState.working,
      },
      {'a': 'security', 'b': 'security', 'c': 'security'},
    );
    expect(counts['security']!.working, 1);
    expect(counts['security']!.waiting, 1);
    expect(counts['security']!.idle, 1);
    expect(counts['web']!.working, 0);
  });
}
