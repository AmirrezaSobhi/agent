# Product version authority — v0.1.5

`agent/__init__.py::__version__` is the canonical stable release version:
`0.1.5`. Agent CLI/Diagnostics, PyInstaller Agent/Worker names and receipts
use it. Desktop and Installer builders read the same authority through
`deployment/Get-MT5AgentVersion.ps1`. The Service/Worker path and .NET metadata
mirrors are checked by `tools/check_product_version.py` before required CI.
Desktop/Service metadata is `0.1.5.0`; pipe protocols stay at version 1.

The Service now launches `Agent/MT5Agent-v0.1.5.exe`; packaged Worker
registration targets `Worker/MT5AgentWorker-v0.1.5.exe`. Service registration
itself still points to `Service/MT5Agent.Service.exe`, so an in-place upgrade
does not rename the SCM service. Existing separately provisioned interactive
Python Workers may be reused only after actual protocol/SID/session validation.
A manifest check of the bundled Worker is not proof that that executable ran.

Pipeline #98 is historical: its Agent/Worker names retained `0.1.3`. It remains
archived and must not be represented as evidence for the newly versioned
binaries. New binary-affecting changes require a new Installer/hash and real
Windows validation. Old product files are not blindly deleted from a VM.

Stable Tag validation still requires exact agreement with the canonical
source version; malformed tags and unrelated commit/pipeline receipts fail.
The unified publisher validates all current-pipeline component hashes,
Installer/Manifest/Sidecar, build/verify job provenance and a real Windows
acceptance receipt for those exact Installer bytes. It does not relabel a
Branch artifact as a Tag-pipeline artifact.

See the [publication runbook](../releases/v0.1.5-release-unblock-runbook.md)
and [release report](../evidence/v0.1.5/V0.1.5_FINAL_RELEASE_REPORT.md).
