import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';

OperationalSnapshot _snapshot({
  List<Map<String, Object?>> liveEvents = const <Map<String, Object?>>[],
  Map<String, Object?> agentState = const <String, Object?>{},
}) => OperationalSnapshot(
      runtimeRoutes: const <Map<String, Object?>>[],
      schedulerState: const <String, Object?>{},
      grantsState: const <String, Object?>{},
      governanceState: const <String, Object?>{},
      evidenceRecords: const [],
      liveEvents: liveEvents,
      agentState: agentState,
    );

void main() {
  test('runtime provenance is accepted only from server-declared agent source', () {
    expect(
      _snapshot(agentState: const <String, Object?>{
        'source': 'canonical-registry+runtime-routes+append-only-readiness-evidence',
      }).agentRuntimeSource,
      'canonical-registry+runtime-routes+append-only-readiness-evidence',
    );
    expect(
      _snapshot(agentState: const <String, Object?>{'source': ' synthetic '})
          .agentRuntimeSource,
      isNull,
    );
  });

  test('live snapshot version is derived only from authoritative event sequence', () {
    expect(
      _snapshot(liveEvents: const <Map<String, Object?>>[
        <String, Object?>{'sequence': 4},
        <String, Object?>{'sequence': 9},
      ]).authoritativeLiveSequence,
      9,
    );
    expect(
      _snapshot(liveEvents: const <Map<String, Object?>>[
        <String, Object?>{'sequence': 4},
        <String, Object?>{'sequence': '5'},
      ]).authoritativeLiveSequence,
      isNull,
    );
  });

  test('freshness uses only authoritative UTC timestamps and fails closed', () {
    final snapshot = _snapshot(
      liveEvents: const <Map<String, Object?>>[
        <String, Object?>{
          'sequence': 1,
          'timestamp': '2026-09-10T14:00:00Z',
        },
      ],
      agentState: const <String, Object?>{
        'agents': <Object?>[
          <String, Object?>{
            'readiness_updated_at': '2026-09-10T14:04:00Z',
          },
        ],
      },
    );

    expect(
      snapshot.authoritativeTimestamp,
      DateTime.parse('2026-09-10T14:04:00Z'),
    );
    expect(
      snapshot.isAuthoritativelyFresh(
        now: DateTime.parse('2026-09-10T14:05:00Z'),
        maxAge: const Duration(minutes: 2),
      ),
      isTrue,
    );
    expect(
      snapshot.isAuthoritativelyFresh(
        now: DateTime.parse('2026-09-10T14:10:00Z'),
        maxAge: const Duration(minutes: 2),
      ),
      isFalse,
    );

    final malformed = _snapshot(
      liveEvents: const <Map<String, Object?>>[
        <String, Object?>{
          'sequence': 1,
          'timestamp': '2026-09-10 14:00:00',
        },
      ],
    );
    expect(malformed.authoritativeTimestamp, isNull);
    expect(
      malformed.isAuthoritativelyFresh(
        now: DateTime.parse('2026-09-10T14:01:00Z'),
        maxAge: const Duration(minutes: 2),
      ),
      isFalse,
    );
  });
}
