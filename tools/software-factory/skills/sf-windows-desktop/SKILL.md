# sf-windows-desktop

Identity: `sf-windows-desktop` v1.0.0, IMPLEMENTED, engineering.

Purpose: specialize canonical Software Factory client work for Windows-first Flutter Desktop implementation, validation, packaging and release-readiness evidence without creating a second App Factory, runtime, signing authority or Store publisher.

Inputs: `intent`, `changed_paths`. Outputs: bounded Windows Desktop change proposal, tests, evidence and unresolved findings.

Specialization:

- preserve the canonical Desktop/client authority boundary;
- compose existing frontend engineering and build/package capabilities rather than duplicating them;
- use only the canonical Flutter RuntimeAdapter for executable validation;
- require Flutter analysis/tests, Windows release build and executable metadata checks for implementation changes;
- require the canonical bundled control-plane sidecar and packaged client-to-runtime E2E when Desktop runtime composition changes;
- require canonical ILAIOS branding derivation and accessibility/behavior contracts;
- require MSIX structure validation when packaging changes;
- treat signing, Partner Center identity, restricted-capability approval and Microsoft Store certification as separate governed/external release dependencies;
- never retrieve signing secrets, publish to the Store, mutate production, bypass governance, or self-certify completion.

PASS means the requested bounded Desktop result is schema-valid and supported by the required repository/runtime evidence. A successful unsigned build never implies signed release or Store publication.

The common `../CONTRACT.md` supplies the shared SF-7 governance and completion gates.