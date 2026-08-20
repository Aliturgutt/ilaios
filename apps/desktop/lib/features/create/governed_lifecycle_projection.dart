import '../../control_plane/operational_snapshot.dart';

enum GovernedLifecycleState {
  unavailable,
  pendingApproval,
  admitted,
  executing,
  accepted,
  blocked,
  denied,
  failed,
}

/// Presentation-only cache of the latest authoritative operational snapshot.
///
/// The cache never creates or advances lifecycle state. It is replaced on each
/// successful control-plane refresh and cleared on refresh failure/sign-out so
/// the UI cannot retain stale execution truth.
class GovernedLifecycleProjectionStore {
  GovernedLifecycleProjectionStore._();

  static OperationalSnapshot _snapshot = const OperationalSnapshot.unavailable();

  static OperationalSnapshot get snapshot => _snapshot;

  static void replace(OperationalSnapshot snapshot) {
    _snapshot = snapshot;
  }

  static void clear() {
    _snapshot = const OperationalSnapshot.unavailable();
  }
}

GovernedLifecycleState resolveGovernedLifecycle(
  OperationalSnapshot snapshot,
  String requestId, {
  String? admittedStatus,
}) {
  final normalizedRequest = requestId.trim();
  if (normalizedRequest.isEmpty || !snapshot.available) {
    return GovernedLifecycleState.unavailable;
  }

  final governance = _matchingGovernance(snapshot.governanceState, normalizedRequest);
  if (governance == 'denied' || governance == 'rejected') {
    return GovernedLifecycleState.denied;
  }
  if (governance == 'pending' || governance == 'reviewing') {
    return GovernedLifecycleState.pendingApproval;
  }
  if (_requiresPendingApproval(snapshot.governanceState, normalizedRequest, governance)) {
    return GovernedLifecycleState.pendingApproval;
  }

  final eventState = _latestMatchingEventState(snapshot.liveEvents, normalizedRequest);
  final schedulerState = _matchingSchedulerState(snapshot.schedulerState, normalizedRequest);
  final state = eventState ?? schedulerState ?? admittedStatus?.trim();
  return _mapState(state);
}

String? _matchingGovernance(Map<String, Object?> state, String requestId) {
  final work = state['work'];
  if (work is! List<Object?>) return null;
  for (final item in work.reversed) {
    if (item is! Map) continue;
    if (item['request_id'] != requestId) continue;
    final value = item['status'];
    if (value is String && value.trim().isNotEmpty) {
      return value.trim().toLowerCase();
    }
  }
  return null;
}

bool _requiresPendingApproval(
  Map<String, Object?> state,
  String requestId,
  String? governance,
) {
  if (governance == 'approved') return false;
  final admissions = state['admissions'];
  if (admissions is! List<Object?>) return false;
  for (final item in admissions.reversed) {
    if (item is! Map) continue;
    if (item['request_id'] == requestId && item['human_approval_required'] == true) {
      return true;
    }
  }
  return false;
}

String? _latestMatchingEventState(
  List<Map<String, Object?>> events,
  String requestId,
) {
  for (final event in events.reversed) {
    final eventRequest = event['request_id'] ?? event['execution_id'];
    if (eventRequest != requestId) continue;
    for (final key in const <String>['execution_status', 'status', 'state']) {
      final value = event[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
  }
  return null;
}

String? _matchingSchedulerState(Map<String, Object?> state, String requestId) {
  final requests = state['requests'] ?? state['work'] ?? state['executions'];
  if (requests is List<Object?>) {
    for (final item in requests.reversed) {
      if (item is! Map) continue;
      final itemRequest = item['request_id'] ?? item['execution_id'];
      if (itemRequest != requestId) continue;
      for (final key in const <String>['execution_status', 'status', 'state']) {
        final value = item[key];
        if (value is String && value.trim().isNotEmpty) return value.trim();
      }
    }
  }
  final directRequest = state['request_id'] ?? state['execution_id'];
  if (directRequest == requestId) {
    for (final key in const <String>['execution_status', 'status', 'state']) {
      final value = state[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
  }
  return null;
}

GovernedLifecycleState _mapState(String? raw) {
  final state = raw?.trim().toUpperCase();
  return switch (state) {
    'PENDING_APPROVAL' || 'AWAITING_APPROVAL' || 'REQUIRE_APPROVAL' =>
      GovernedLifecycleState.pendingApproval,
    'ADMITTED' => GovernedLifecycleState.admitted,
    'EXECUTING' || 'RUNNING' => GovernedLifecycleState.executing,
    'ACCEPTED' || 'VERIFIED' => GovernedLifecycleState.accepted,
    'DENIED' || 'REJECTED' => GovernedLifecycleState.denied,
    'FAILED' => GovernedLifecycleState.failed,
    final value when value != null && value.startsWith('BLOCKED_') =>
      GovernedLifecycleState.blocked,
    _ => GovernedLifecycleState.unavailable,
  };
}
