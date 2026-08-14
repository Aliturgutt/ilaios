# ILAIOS Desktop

Windows-first Flutter/Dart client for the ILAIOS control plane.

## Authority boundary

ILAIOS Desktop is a governed client. The backend/control plane remains authoritative for authorization, policy, tenant isolation, governance, scheduling, execution, grants, evidence verification, and critical decisions. The Desktop client may express user intent and explicitly retrieve an already verified delivery, but it does not fabricate capabilities, mint execution authority, select privileged workers/providers, or mark work complete locally.

The client does not accept a client-selected tenant identifier or tenant override. Tenant scope is determined by authenticated backend/control-plane context; Desktop cannot widen or override that scope locally.

The client accepts only loopback HTTP control-plane endpoints (`127.0.0.1`, `::1`, or `localhost`). Operational state is cleared when authoritative refresh fails so stale state is not presented as current.

## Packaged Windows runtime

A production Windows build contains `ilaios_control_plane.exe`, a packaged entrypoint for the canonical Python control plane. It is not a second runtime or alternative authority.

When no trusted external control-plane configuration is supplied, Desktop:

1. creates a cryptographically strong per-process local bearer token in memory;
2. starts the bundled control-plane executable on loopback with an ephemeral port;
3. stores durable local control-plane state under the current user's local application-data area;
4. waits for the canonical readiness file; and
5. connects only after a valid loopback endpoint is reported.

The token is passed to the child process through the process environment and is not written to the readiness file or committed to the repository. The bundled child process is stopped when the Desktop bootstrap is disposed.

For trusted development/operations, explicit runtime configuration remains supported:

- `ILAIOS_CONTROL_PLANE_TOKEN` — bearer token. Do not commit or log this value.
- `ILAIOS_CONTROL_PLANE_URL` — optional explicit loopback URL, for example `http://127.0.0.1:4123`.
- `ILAIOS_CONTROL_PLANE_READY_FILE` — optional readiness JSON file containing `host` and `port` when an explicit URL is not supplied.
- `ILAIOS_APPROVER_ID` — optional independent human approver identity. Governance controls remain disabled when it is absent.

## Product surfaces

### Create

`Create` is the one-prompt intake surface. It sends the user's objective to the current authoritative goal endpoint and then creates a durable job bound to that goal. The client does not choose the provider/model/worker and does not interpret a created or pending job as a finished product.

The current repository API reality used by Desktop is:

```text
POST /v1/goals
POST /v1/jobs
GET  /v1/jobs/{job_id}
```

The richer project-scoped public API documented in canonical API contracts remains target truth until separately implemented and verified.

### Live execution, governance and evidence

Existing operational surfaces continue to project authenticated runtime, scheduler, grants, governance, evidence and live-event state. Approval buttons send only an approve/deny decision to the authoritative governance gateway. Secret references are not rendered.

### Deliveries

`Deliveries` lists only artifact identities already present in the verified evidence projection. Saving is always an explicit user action. Desktop requests bytes through the authoritative evidence endpoint and writes the returned verified artifact to the user's delivery directory using a digest-bound filename. Raw base64 is never rendered in the UI.

Current evidence retrieval API:

```text
GET /v1/evidence/artifacts/{sha256}
```

## Identity boundary

The current bundled local control-plane token is an internal Desktop-to-sidecar transport credential, not a human Google/Microsoft/email identity and not a tenant authorization substitute. Public account sign-in must be implemented through the canonical identity/session boundary with cryptographically verified federation/session semantics; Desktop must not locally trust unverified IdP claims.

No Google, Microsoft, email/magic-link, Store identity, or external certification is claimed by the existence of the local transport token.

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

The Windows Gate additionally:

1. builds the bundled canonical control-plane executable;
2. starts that packaged executable in an isolated temporary data root;
3. runs a real Dart client → packaged control-plane E2E that creates an authoritative goal and job and reads them back; and
4. validates the Desktop executable metadata and sidecar presence.

Unsigned MSIX packaging builds the Desktop executable plus bundled control-plane executable, unpacks the result and validates the package structure. The resulting CI package is an internal validation artifact only; it is not a signed or Store-published release.

For a Windows-local release gate, run `tool/validate_windows_release.ps1` from this directory.

## Distribution boundary

The repository has a fail-closed signed-MSIX workflow, but a signed release is not proven until trusted publisher identity, package identity and signing secrets are deliberately provisioned and that workflow passes for the exact release revision.

Microsoft Store publication, account identity verification, Store certification, restricted-capability approval, privacy/age-rating declarations and external compliance remain separate release dependencies. They must not be inferred from application, Windows Gate or unsigned-MSIX success.

## Known external/product dependencies

- Public Google/Microsoft/email account sign-in requires an approved identity-provider/broker configuration and verified session integration.
- Signed MSIX proof requires real publisher/package identity and protected signing material.
- Microsoft Store publication requires Partner Center account/submission actions and certification.
- Factory-specific native executors may have additional packaged-runtime dependencies; their availability must be proven by their own governed capability/release gates rather than inferred from the Desktop shell.

## Scope

This package is ILAIOS Desktop only. It does not own Website/Vercel/DNS configuration and OpenClaw is not a runtime dependency.
