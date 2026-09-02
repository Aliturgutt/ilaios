# ILAIOS Desktop — Pre-Store 98% Closure Checklist

Status authority: repository code, tests, CI, packaged runtime evidence, and final real-Windows acceptance override this planning checklist.

Goal: complete every deterministic Desktop task that does not require Microsoft Partner Center business-verification completion, publisher/package identity assignment, signing secrets, legal declarations, or final Store certification submission.

## A. Premium product shell and canonical branding

- [x] Merge the premium target control-center UI into `master`.
- [x] Bind Desktop UI tokens to the canonical ILAIOS neutral palette: Carbon `#0A0A0A`, Charcoal `#141414`, Graphite `#1E1E1E`, Stone `#2A2A2A`, White `#FFFFFF`, Text Secondary `#E6E6E6`, Text Tertiary `#B3B3B3`, Disabled `#808080`, Hover `#242424`, Active `#2F2F2F`. ILAIOS Cyan `#00C2D1` and ILAIOS Blue `#146BFF` are reserved for official logo/icon identity only and are not UI accents.
- [x] Use the canonical ILAIOS symbol/app-icon sources for the Flutter shell, Windows executable icon, and MSIX asset derivation without redrawing/recoloring.
- [ ] Re-run exact-head responsive/text-scaling layout gates after final pre-Store changes.

## B. Account identity and session continuity

- [x] Google OIDC Authorization Code + PKCE integration exists and real Windows sign-in has been user-validated.
- [x] Google protected refresh credential/session restore exists and real Windows 3/3 restart persistence has been user-validated.
- [ ] Add Microsoft public-client OIDC code readiness using system-browser Authorization Code + S256 PKCE, no embedded client secret, and `offline_access` for refresh continuity.
- [ ] Support Microsoft v2 multitenant/personal-account issuer-template verification (`{tenantid}`) with `tid`/issuer/signing-key-issuer binding.
- [ ] Generalize DPAPI-protected refresh persistence to Microsoft without weakening Google behavior.
- [ ] Add Microsoft-specific negative tests for nonce, audience, tenant/issuer mismatch, signing-key issuer mismatch, refresh rotation, and logout clearing.
- [ ] Document the exact external Microsoft app-registration values that remain human-supplied; do not invent a client ID or secret.
- [ ] Real Microsoft sign-in + 3/3 restart persistence is final-Windows acceptance and remains blocked until a real Microsoft app registration/client ID is supplied.

## C. Runtime truth and operational surfaces

- [ ] Verify Home/workflow/worker/status/cost/approvals/log/artifact/evidence widgets render authoritative populated snapshots as well as truthful empty states.
- [ ] Verify no synthetic project, worker, cost, token/GPU, progress, log, artifact, evidence, or completion claim is introduced by presentation code.
- [ ] Keep Live Code/Browser unavailable when the current authoritative API exposes no such projection; do not fabricate preview content.
- [ ] Verify all navigation destinations remain reachable and fail closed when authoritative state is unavailable.

## D. Windows UX quality gates

- [ ] Verify target composition at 1920×1080, 1600×900, 1280×720, 1024×720, and compact supported widths.
- [ ] Verify 125% and 150% text scaling without RenderFlex overflow.
- [ ] Verify keyboard/focus/semantic labels for core navigation, refresh, identity, and primary action surfaces where applicable.
- [ ] Verify loading, empty, disconnected, unavailable, and error states are explicit and non-misleading.

## E. Windows identity, icons, package and provenance

- [x] Native executable metadata identifies ILAIOS Desktop.
- [x] Windows `.ico` derivation is automated from the canonical app icon and includes multi-resolution frames.
- [x] MSIX Store/tile assets are derived from the canonical app-icon master.
- [ ] Re-verify EXE icon metadata, title, bundled sidecar, exact source SHA, and package structure on final exact head.
- [ ] Re-run unsigned MSIX packaging and checksum generation on final exact head.
- [ ] Keep signed release fail-closed until Partner Center publisher/package identity and protected signing material exist.

## F. Security/regression/release evidence

- [ ] Run Python identity/persistence tests and strict typing/lint gates affected by Microsoft readiness changes.
- [ ] Run Flutter analyze/tests and Desktop Windows build gate.
- [ ] Run Required CI Gate, Software Factory Final Evidence, Desktop CI, Desktop Windows Gate, and Desktop MSIX Packaging on the exact final pre-Store SHA.
- [ ] Merge only when required exact-head checks pass.

## G. Final real-Windows acceptance after deterministic closure

Perform once, after all repository/CI items above are green:

- [ ] Install one fresh exact-head Desktop package on the user's Windows machine.
- [ ] Compare the real Desktop against the approved premium target reference; fix only evidence-backed visual defects.
- [ ] Confirm canonical ILAIOS colors/logo, taskbar/window/shortcut identity, responsive layout, and no duplicate/stale shortcut behavior.
- [ ] Reconfirm Google 3/3 restart persistence.
- [ ] When Microsoft app registration is available, confirm Microsoft sign-in and Microsoft 3/3 restart persistence.
- [ ] Run one real governed workflow and confirm agents/workers, progress, logs, artifacts, evidence, approvals and available cost state are sourced from authoritative runtime data.

## H. External Microsoft/Store work — excluded from the 98% deterministic target

These remain intentionally external until Microsoft business verification and Partner Center identity are available:

- Partner Center business-verification completion.
- Store product reservation / assigned package Identity Name and Publisher string.
- Human-required age rating, markets/pricing, privacy/support declarations, and restricted-capability answers.
- Protected signing credential provisioning when applicable.
- Final signed/package-identity proof where required.
- Final Microsoft Store submission and certification acceptance.

The Desktop must not be called 100% Store-released until these external gates and final real-Windows acceptance pass.