# Local Control Plane Operations

The authoritative local command/query/event boundary runs as a loopback-only
HTTP process. It owns durable SQLite state; Desktop and Web clients remain
non-authoritative projections.

Set `ILAIOS_CONTROL_PLANE_TOKEN` through the local process environment, then
start the service with explicit state and readiness paths:

```bash
python -m services.control_plane.server \
  --database var/control-plane.sqlite3 \
  --ready-file var/control-plane-ready.json
```

The process rejects non-loopback bind addresses. Every `/v1` command, query,
and event request requires `Authorization: Bearer <token>`. The readiness file
contains only the selected loopback address, ephemeral or configured port, and
the applied schema version; it never contains the token.

Schema migration is explicit and idempotent:

```bash
python -m services.control_plane.migrations upgrade \
  --database var/control-plane.sqlite3
```

Rollback always requires a new backup path. The database is copied before one
schema version is reversed, and the original is restored automatically if the
down migration fails:

```bash
python -m services.control_plane.migrations rollback \
  --database var/control-plane.sqlite3 \
  --backup var/control-plane-before-rollback.sqlite3
```

Restore after a completed rollback by stopping the service, retaining the
rolled-back database for evidence, copying the verified backup into the
configured database path, and restarting the process. This procedure is local
only and does not change `ReleaseState.NOT_DEPLOYED`.
