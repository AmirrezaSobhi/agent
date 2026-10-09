# MT5Agent Desktop distribution

This directory retains the v0.1.5 Desktop-only ZIP as a diagnostic artifact.
The intended user-facing delivery is now the unified Setup executable built by
`installer:build` under `deployment/installer/`.

The CI package is `MT5Agent-Desktop-v0.1.5-windows-x64.zip`. Download it from
the `desktop:build-package` job under `dist/desktop/`; the package verification
job consumes the exact same archive and publishes only its verification
report. The version-aware branch artifact URL is
`https://gitlab.local/root/agent/-/jobs/artifacts/feat%2Fv0.1.5-desktop-integration/download?job=desktop%3Abuild-package`.
The embedded manifest records the source commit, GitLab pipeline and build job,
framework requirement, packaged file hashes, and the WPF executable hash.
`SHA256SUMS.txt` covers every payload file and the manifest; the checksum file
does not hash itself.

Use `INSTALL.md` inside the archive for first install, replacement, rollback,
and removal. The package is unsigned; it is an internal test distribution, not
a public release artifact.
