# ILAIOS Desktop

Windows-first Flutter/Dart client for the ILAIOS control plane.

## Authority boundary

ILAIOS Desktop is a secure projection client. The backend/control plane remains authoritative for authorization, policy, tenant isolation, governance, scheduling, execution, grants, evidence verification, and critical decisions. The Desktop client does not fabricate capabilities or execute governed work locally.

The client accepts only an explicit loopback HTTP control-plane endpoint (`127.0.0.1`, `::1`, or `localhost`) and requires a bearer token before authenticated APIs are queried. Operational state is cleared when authoritative refresh fails so stale state is not presented as current.

## Runtime configuration

Configuration is provided to the process by the trusted launcher/runtime environment:

- `ILAIOS_CONTROL_PLANE_TOKEN` — required bearer token. Do not commit or log this value.
- `ILAIOS_CONTROL_PLANE_URL` — optional explicit loopback URL, for example `http://127.0.0.1:4123`.
- `ILAIOS_CONTROL_PLANE_READY_FILE` — optional readiness JSON file containing `host` and `port` when an explicit URL is not supplied.
- `ILAIOS_APPROVER_ID` — optional independent human approver identity. Governance controls remain disabled when it is absent.

The Desktop UI never renders control-plane secret references and only displays verified evidence metadata, not artifact bytes/base64 content.

## Canonical branding

Runtime UI branding uses the canonical repository asset `brand/assets/05-ilaios-app-icon.jpg`. The Windows `.ico` resource is generated during the Windows build by `tool/generate_windows_icon.ps1` using scale-only transforms; no crop, recolor, redraw, or geometry modification is permitted.

## Validation

From `apps/desktop`:

```text
flutter pub get --enforce-lockfile
flutter analyze
flutter test
flutter build windows --release
```

The repository GitHub Actions Windows gate pins Flutter `3.44.9` to revision `6b182d2c7585eba26d4edce0f97630effd256c33`, runs static analysis and tests, builds the Windows release executable, and validates executable metadata.

For a Windows-local release gate, run `tool/validate_windows_release.ps1` from this directory.

## Scope

This package is ILAIOS Desktop only. It does not own Website/Vercel/DNS configuration and OpenClaw is not a runtime dependency.
