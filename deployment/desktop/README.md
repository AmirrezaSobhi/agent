# MT5Agent Desktop distribution

This directory contains the v0.1.4 user-scope WPF package tooling. It builds
only `MT5Agent.Desktop`; it does not install, replace, configure, or stop the
Python Agent, Windows Service, Runtime Worker, MT5 terminal, or user account.

The CI package is `MT5Agent-Desktop-v0.1.4-windows-x64.zip`. Its embedded
manifest records the source commit, GitLab pipeline and build job, framework
requirement, packaged file hashes, and the WPF executable hash. `SHA256SUMS.txt`
covers every payload file and the manifest; the checksum file does not hash
itself.

Use `INSTALL.md` inside the archive for first install, replacement, rollback,
and removal. The package is unsigned; it is an internal test distribution, not
a public release artifact.
