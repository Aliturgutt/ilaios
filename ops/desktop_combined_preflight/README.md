# Desktop Combined Preflight

This branch exists only to prove the Windows PowerShell 5.1 native-process boundary that previously caused the local Desktop combined installer to fail before patch/build/install.

Acceptance criteria:

- `git clone` must succeed under Windows PowerShell 5.1 with `$ErrorActionPreference = 'Stop'` while Git writes normal progress text to STDERR.
- The wrapper must use the native process exit code as authority, not STDERR text.
- The six Desktop files targeted by the combined typography/reference UX patch must still match the validated blob SHAs on current `master`.

No production/runtime completion claim is made by this preflight alone.
