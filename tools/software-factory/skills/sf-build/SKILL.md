# sf-build

Identity: `sf-build` v1.0.0, IMPLEMENTED, build-release-operations.

Purpose: drive canonical SF-6 build/package validation and emit source-bound artifact evidence. Inputs: `intent`, `changed_paths`. Outputs: artifact references/hashes, source/base binding, runtime evidence.

Specialization: use RuntimeAdapter only; no direct command-spawn fallback, no publication, and no source/artifact evidence without base binding.

The common `../CONTRACT.md` applies.
