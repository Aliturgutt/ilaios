# ILAIOS Desktop — `runFullTrust` Store rationale

Status: PREPARED, NOT SUBMITTED, NOT APPROVED.

ILAIOS Desktop is a Flutter-based Windows desktop client packaged as MSIX. The package launches the compiled `ilaios_desktop.exe` desktop executable with the manifest entry point `Windows.FullTrustApplication`. The `runFullTrust` declaration is used only to permit that classic desktop application model to run from the MSIX package.

The capability is not intended to grant ILAIOS Desktop independent system authority. Product authorization, policy, governance, tenant boundaries, and critical execution decisions remain backend/control-plane responsibilities. The client must not claim or infer privileges beyond the operating-system permissions actually granted to the installed process.

For Microsoft Store submission, the authorized publisher must review this rationale against the shipping binary and current Microsoft restricted-capability policy, then provide an accurate explanation in Partner Center. Any additional privileged behavior discovered before submission must be documented separately; this file must not be used to conceal or generalize unrelated privileged functionality.

No Store approval is asserted by this document.