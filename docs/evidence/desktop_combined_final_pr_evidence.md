# Desktop Combined Final PR Evidence

Status: IN PROGRESS

This branch exists to verify the Desktop typography uplift plus compact Web/Video reference UX on Windows before any user-machine install command is issued.

Acceptance gates:

- fail-closed patch application on current source
- no protected shell geometry rewrite
- Flutter analyze PASS
- required 1366x768, 1440x900, 1920x1080 widget regression PASS
- full Desktop Flutter tests PASS
- Windows release build PASS
- bundled control-plane sidecar PASS
- executable metadata verification PASS
- CI artifact contains portable runtime, SHA256 manifest, evidence, and rollback-capable installer

No runtime/DONE claim is allowed until the CI artifact is produced and the installed executable survives the user-machine runtime smoke.
