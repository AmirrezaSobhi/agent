# Product and component versioning — v0.1.5 candidate

The product/Installer and Desktop version are `0.1.5` (`0.1.5.0` for WPF
assembly metadata). The Python Core's reported version and Agent/Worker
executable names retain the `0.1.3` component line. Runtime/Management protocol
version 1 is separate from both. A component filename does not identify its
exact source build: the pipeline manifest and SHA-256 do.

The documented candidate policy retains these component names to preserve the
existing Service, scheduled-task, runtime and uninstall path contracts. It
does not rename an installed executable or imply the old `v0.1.3` release binary
is packaged: Pipeline #98's exact hashes identify the updated components.
The preinstalled interactive Python Worker was reused; a manifest check of
the bundled Worker executable is not proof that this packaged Worker ran.

## Existing dependency contracts

- `agent/__init__.py` and Python package metadata report `0.1.3`.
- `deployment/ci.ps1` derives build names and version receipts from that field.
- `deployment/service/Program.cs` launches `MT5Agent-v0.1.3.exe`.
- Installer/Worker provisioning scripts and manifests consume those exact
  component paths; Registry/Task configuration is machine-local.
- Desktop and Installer independently record product version `0.1.5`.
- The legacy tag/publisher contract assumes product and Core versions are
  equal. `v0.1.5` is therefore currently rejected by tag validation and the
  publisher, which also publishes only a standalone Agent executable.

## Release defect and required resolution

The component naming is runtime-compatible in the tested installation, but
the official product release contract remains **BLOCKED**. A product publisher
must validate the product version, component versions, complete Installer
manifest, checksums, test receipts, protected-main lineage and independent
approval together. Existing Core version/hash gates must remain effective;
merely deleting the tag/version comparison is not a solution.

The exact #98 Installer remains the frozen operational candidate. Its manifest
must retain source commit `54f47a6dad8541984b3930051cb6610f85bb95cc` and Pipeline
98. Any future promotion of that candidate must explicitly preserve this
provenance rather than relabel it as a Main/Tag build. Binary-affecting changes
require a new verified artifact and appropriate real Windows validation.
No version/path code changes were made by the blocked release audit.

See the [final release audit](../evidence/v0.1.5/V0.1.5_FINAL_RELEASE_REPORT.md).
