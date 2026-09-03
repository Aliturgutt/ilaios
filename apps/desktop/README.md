# ILAIOS Desktop

Windows-first Flutter/Dart client for the ILAIOS control plane.

## Authority boundary

ILAIOS Desktop is a governed client. The backend/control plane remains authoritative for authorization, policy, tenant isolation, governance, scheduling, execution, grants, evidence verification, and critical decisions. The Desktop client may express user intent and explicitly retrieve an already verified delivery, but it does not fabricate capabilities, mint execution authority, select privileged workers/providers, or mark work complete locally.

The client does not accept a client-selected tenant identifier or tenant override. Tenant scope is determined by authenticated backend/control-plane context; Desktop cannot widen or override that scope locally.

The client accepts only loopback HTTP control-plane endpoints (`127.0.0.1`, `::1`, or `localhost`). Operational state is cleared when authoritative refresh fails so stale state is not presented as current.

## Packaged Windows runtime

A production Windows build contains `ilaios_control_plane.exe`, a packaged entrypoint for the canonical Python control plane plus the loopback Desktop identity adapter. The adapter is not a second execution runtime or alternative authority.

When no trusted external control-plane configuration is supplied, Desktop:

1. creates a cryptographically strong per-process local bearer token in memory;
2. starts the bundled control-plane executable on loopback with ephemeral ports;
3. stores durable local control-plane state under the current user's local application-data area;
4. waits for canonical control-plane and identity-adapter readiness; and
5. connects only after valid loopback endpoints are reported.

The local transport token is passed to the child process through the process environment and is not written to the readiness file or committed to the repository. The bundled child process is stopped when the Desktop bootstrap is disposed.

For trusted development/operations, explicit runtime configuration remains supported:

- `ILAIOS_CONTROL_PLANE_TOKEN` — bearer token. Do not commit or log this value.
- `ILAIOS_CONTROL_PLANE_URL` — optional explicit loopback URL, for example `http://127.0.0.1:4123`.
- `ILAIOS_CONTROL_PLANE_READY_FILE` — optional readiness JSON file containing runtime endpoints when an explicit URL is not supplied.
- `ILAIOS_IDENTITY_URL` — optional explicit loopback Desktop identity-adapter URL.
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

When external account providers are configured, prompt submission first requires a valid ILAIOS Desktop user session and flows through the identity adapter before the adapter forwards the bounded intent to the same canonical control plane.

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

The bundled local control-plane bearer token is only an internal Desktop-to-sidecar transport credential. Human account sign-in is implemented separately through a provider-neutral OIDC Authorization Code + PKCE adapter that composes the canonical `services.identity` verification/session boundary.

The adapter requires HTTPS provider authority, uses state, nonce and S256 PKCE, verifies signed ID tokens through provider JWKS, validates issuer/audience/token time claims, derives an ILAIOS principal/tenant projection, and issues an in-memory ILAIOS session whose lifetime cannot exceed the verified identity token. Raw identity-provider tokens are not returned to Flutter.

Packaged Windows builds include the approved **non-secret public registration metadata** needed for already-validated providers in `packaging/identity/oidc-providers.public.json`. Public OAuth client IDs are identifiers, not bearer credentials; the packaged metadata is audited to reject any `client_secret`. Trusted development/operations can override the packaged list with `ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON` when a different test registration is deliberately required.

The current packaged default contains the validated Google Desktop public registration. Microsoft support is code-ready for a native public client, but Microsoft is not added to the packaged default until the real Microsoft Application (client) ID is assigned and deliberately supplied. Microsoft Desktop registration rejects an embedded client secret and uses `offline_access` plus Windows DPAPI-protected refresh continuity.

Passwordless/email sign-in may be exposed through an approved OIDC identity broker that provides verified email federation. Without approved provider registration, Desktop must truthfully report that provider as unavailable and must not invent an external identity.

See `docs/platform/desktop/MICROSOFT_OIDC_SETUP.md` for the exact Microsoft external registration contract and the real-Windows acceptance boundary.

## Canonical branding

Desktop horizontal branding uses `brand/assets/02-ilaios-primary-horizontal-dark.jpg` on Dark surfaces and `brand/assets/13-ilaios-primary-horizontal-light.jpg` on Light surfaces. Theme-aware symbol/app-icon presentation uses the `05` Dark and `04` Light pair where a symbol/icon is required. Windows executable/MSIX icon packaging remains separate: the Windows `.ico` resource is generated from `brand/assets/05-ilaios-app-icon.jpg` by `tool/generate_windows_icon.ps1` using scale-only transforms; no crop, recolor, redraw, or geometry modification is permitted.

Desktop theme tokens use the canonical ILAIOS palette rather than feature-local colors. Semantic success/warning/error colors remain distinct from brand accents so system meaning is not conflated with branding.

## Validation

From `apps/desktop`:

```text
flutter pub get --enforce-lockfile
flutter analyze
flutter test
flutter build windows --release
```

The Windows Gate additionally:

1. builds the bundled canonical control-plane/identity sidecar;
2. starts that packaged executable in an isolated temporary data root;
3. verifies packaged public identity provider metadata through the real loopback identity endpoint;
4. runs a real Dart client → packaged runtime E2E that validates the identity-adapter transport, creates an authoritative goal and job, and reads the job/projection back; and
5. validates the Desktop executable metadata and sidecar presence.

Unsigned MSIX packaging builds the Desktop executable plus bundled control-plane executable, unpacks the result and validates the package structure. The resulting CI package is an internal validation artifact only; it is not a signed or Store-published release.

For a Windows-local release gate, run `tool/validate_windows_release.ps1` from this directory.

## Distribution boundary

The repository has a fail-closed signed-MSIX workflow, but a signed release is not proven until trusted publisher identity, package identity and signing secrets are deliberately provisioned and that workflow passes for the exact release revision.

Microsoft Store publication, account/provider production approval where required, Store certification, restricted-capability approval, privacy/age-rating declarations and external compliance remain separate release dependencies. They must not be inferred from application, Windows Gate or unsigned-MSIX success.

## Known external/product dependencies

- Microsoft account sign-in requires the real Microsoft App Registration / public Application (client) ID plus real-Windows acceptance; Google or other identity providers may also have provider-side production/publishing requirements independent of Desktop code.
- Signed MSIX proof requires real publisher/package identity and protected signing material.
- Microsoft Store publication requires Partner Center account/submission actions and certification.
- Factory-specific native executors may have additional packaged-runtime dependencies; their availability must be proven by their own governed capability/release gates rather than inferred from the Desktop shell.

## Scope

This package is ILAIOS Desktop only. It does not own Website/Vercel/DNS configuration and OpenClaw is not a runtime dependency.
