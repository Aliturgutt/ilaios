# ILAIOS Desktop

Windows-first Flutter/Dart client for the ILAIOS control plane.

## Authority boundary

ILAIOS Desktop is a governed client. The backend/control plane remains authoritative for authorization, policy, tenant isolation, governance, scheduling, execution, grants, evidence verification, and critical decisions. The Desktop client may express user intent and explicitly retrieve an already verified delivery, but it does not fabricate capabilities, mint execution authority, select privileged workers/providers, or mark work complete locally.

The client does not accept a client-selected tenant identifier or tenant override. Tenant scope comes from the verified ILAIOS session; Desktop cannot widen or override that scope locally.

The client accepts only loopback HTTP control-plane endpoints (`127.0.0.1`, `::1`, or `localhost`). Operational state is cleared when authoritative refresh fails so stale state is not presented as current.

## Packaged Windows runtime

A Windows build contains `ilaios_control_plane.exe`, a packaged composition root for the canonical Python Control Plane plus the loopback Desktop identity adapter and one-prompt execution coordinator. These components share the same canonical governance, scheduler, grants, evidence and finished-product runtime objects; the adapter/coordinator do not create a second Core, runtime, scheduler or factory.

When no trusted external control-plane configuration is supplied, Desktop:

1. creates a cryptographically strong per-process local bearer token in memory;
2. starts the bundled control-plane executable on loopback with ephemeral ports;
3. stores durable local control-plane state under the current user's local application-data area;
4. waits for canonical control-plane and identity-adapter readiness; and
5. connects only after valid loopback endpoints are reported.

The local transport token is passed to the child process through the process environment and is not written to the readiness file or committed to the repository. It is a transport credential, not a human identity. The bundled child process is stopped when the Desktop bootstrap is disposed.

For trusted development/operations, explicit runtime configuration remains supported:

- `ILAIOS_CONTROL_PLANE_TOKEN` — bearer token. Do not commit or log this value.
- `ILAIOS_CONTROL_PLANE_URL` — optional explicit loopback URL, for example `http://127.0.0.1:4123`.
- `ILAIOS_CONTROL_PLANE_READY_FILE` — optional readiness JSON file containing runtime endpoints when an explicit URL is not supplied.
- `ILAIOS_IDENTITY_URL` — optional explicit loopback Desktop identity-adapter URL.
- `ILAIOS_APPROVER_ID` — optional independent human approver identity. Governance controls remain disabled when it is absent.

## Product surfaces

### Create

`Create` is the one-prompt intake surface. Governed product execution is enabled only after a verified account session exists. The Flutter client submits the objective to the loopback identity broker together with the short-lived ILAIOS session identifier; it does not send a client-selected principal or tenant.

The broker validates the session and calls the canonical `ExecutionCoordinator` with the authoritative `principal_id` and `tenant_id`. The coordinator creates the durable goal/job/proposal and selects a canonical capability conservatively. Ambiguous or unknown prompts fail closed rather than guessing.

Current execution-adapter reality in this workstream:

- Video/Media Factory: bound to the existing governed `DurableVideoProductRuntime`; it creates governance work and remains `PENDING_APPROVAL` until independent approval is proven.
- Web, App, Software, Research/Data, Creative/Document, Commerce/Growth, Personal Operations and Security: capability classification exists, but no finished-product execution adapter is claimed here. These requests stop as `BLOCKED_ADAPTER_UNAVAILABLE` after durable goal/job/proposal creation.

This distinction is intentional. A capability being present in the registry does not prove that a complete one-prompt finished-product adapter exists.

After a coordinator-created high-risk request is independently approved, Desktop explicitly asks the identity broker to resume that same request. The broker revalidates session ownership and the coordinator rechecks durable approval before issuing a bounded execution grant and acquiring a fresh scheduler lease. Submission, approval and execution are therefore separate authority transitions.

### Live execution, governance and evidence

Existing operational surfaces continue to project authenticated runtime, scheduler, grants, governance, evidence and live-event state. Approval buttons send only an approve/deny decision to the authoritative governance gateway. A coordinator request is resumed only after that durable decision succeeds. Secret references are not rendered.

### Deliveries

`Deliveries` lists only artifact identities already present in the verified evidence projection. Saving is always an explicit user action. Desktop requests bytes through the authoritative evidence endpoint and writes the returned verified artifact to the user's delivery directory using a digest-bound filename. Raw base64 is never rendered in the UI.

Current evidence retrieval API:

```text
GET /v1/evidence/artifacts/{sha256}
```

## Identity boundary

The bundled local control-plane bearer token is only an internal Desktop-to-sidecar transport credential. Human account sign-in is implemented separately through a provider-neutral OIDC Authorization Code + PKCE adapter that composes the canonical `services.identity` verification/session boundary.

The adapter requires HTTPS provider authority, uses state, nonce and S256 PKCE, verifies signed ID tokens through provider JWKS, validates issuer/audience/token time claims, derives an ILAIOS principal/tenant projection, and issues an in-memory ILAIOS session whose lifetime cannot exceed the verified identity token. Raw identity-provider tokens are not returned to Flutter.

Provider registration is external configuration supplied through `ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON`; no provider client secret is accepted. Google and Microsoft may be configured as native public OIDC clients. Passwordless/email sign-in may be exposed through an approved OIDC identity broker that provides verified email federation. Without approved provider registration, Desktop truthfully reports account sign-in as not configured and governed one-prompt execution remains disabled; no fallback identity is fabricated.

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

The Windows Gate additionally builds the packaged sidecar and runs a real Dart client against it. With no external OIDC provider configured, that E2E must prove both sides of the boundary: the canonical low-level Control Plane remains reachable, while a fabricated Desktop session cannot use the identity broker to start governed execution.

`tests/test_execution_coordinator.py` exercises the coordinator against the real durable Control Plane/governance/scheduler/grant/video components. Its delayed-approval case is designed to prove that execution obtains a fresh lease after approval instead of relying on a lease created before a human decision.

These tests are code-level validation requirements. This branch must not be described as verified or production until the exact-head CI/Windows/MSIX gates actually run and pass.

Unsigned MSIX packaging builds the Desktop executable plus bundled control-plane executable, unpacks the result and validates the package structure. The resulting CI package is an internal validation artifact only; it is not a signed or Store-published release.

For a Windows-local release gate, run `tool/validate_windows_release.ps1` from this directory.

## Distribution boundary

The repository has a fail-closed signed-MSIX workflow, but a signed release is not proven until trusted publisher identity, package identity and signing secrets are deliberately provisioned and that workflow passes for the exact release revision.

Microsoft Store publication, account/provider registration, Store certification, restricted-capability approval, privacy/age-rating declarations and external compliance remain separate release dependencies. They must not be inferred from application, Windows Gate or unsigned-MSIX success.

## Known external/product dependencies

- Google/Microsoft/passwordless-email account sign-in requires approved provider or broker registration and public client identifiers/configuration.
- Signed MSIX proof requires real publisher/package identity and protected signing material.
- Microsoft Store publication requires Partner Center account/submission actions and certification.
- Finished-product adapters beyond the currently bound Video/Media path require their own implementation and verification; registry presence alone is not execution proof.
- Exact-head GitHub CI/Windows/MSIX verification depends on GitHub Actions being able to start repository jobs.

## Scope

This package is ILAIOS Desktop only. It does not own Website/Vercel/DNS configuration and OpenClaw is not a runtime dependency.
