# GitLab CI and local validation

**Phase 4D status:** IMPLEMENTED; LOCAL VALIDATION PASSED; LIVE CI ACCEPTANCE
PENDING. No first live GitLab pipeline, pipeline/job ID, or release receipt is
claimed here. Update this status only from retained pipeline evidence.

GitLab (`origin`) is the source of truth. CI validates candidate artifacts; it
does not merge, tag, or publish a release. Existing release tags remain
immutable.

## Runner responsibilities

| Runner tag | Role | Expected environment |
| --- | --- | --- |
| `linux-source-unit` | Portable source/unit tests | Linux shell Runner; no MT5 or Windows dependency |
| `windows-self-hosted-no-mt5` | Windows tests, clean Agent build, degraded control-plane smoke, packaging | Windows `pwsh`; MetaTrader5 absent from the isolated Agent build environment |
| `windows-self-hosted-mt5` | Real runtime integration | Session 0 control process authenticated to the persistent interactive Runtime Worker |

All Runners use explicit tags and `run_untagged = false`. The Linux Runner
uses its own GitLab checkout/build workspace, not the developer's authoritative
working tree. `MT5_AGENT_WORKER_PRINCIPAL` is local Runner/machine policy and is
not defined as a global GitLab CI variable.

## Dependency boundary

The Agent build and Windows control-plane jobs install `requirements-dev.txt`.
The production Agent dependency closure excludes MetaTrader5 and NumPy. The
interactive Worker is provisioned separately using `requirements-mt5-worker.txt`
(`MetaTrader5==5.0.6231`, NumPy 2.4.6, and pywin32 312 on Windows). The explicit
legacy in-process adapter dependency set is `requirements-legacy-mt5.txt` and
must not be installed into the production Agent build environment.

The Linux job installs requirements into its job-local target directory and
checks that MetaTrader5 and NumPy are absent. It runs the portable suite while
excluding `tests/test_windows_worker_launcher.py`, which imports Windows-only
modules during collection. The Windows no-MT5 Runner runs the Windows-compatible
suite and the isolated PyInstaller build.

## Pipeline and artifact provenance

```text
Linux source/unit ─┐
                   ├─> Windows no-MT5 tests ─> one clean Agent build
Windows validation┘                               │
                                                  ├─> invalid-configuration smoke
                                                  ├─> degraded no-Worker control-plane smoke
                                                  └─> exact artifact + evidence
                                                           ↓
                                               Windows real-MT5 integration
                                                           ↓
                                               no-rebuild package evidence
```

The build job checks the isolated build environment for MetaTrader5 and NumPy,
builds `MT5Agent-v<version>.exe` once, and inspects the PyInstaller archive for
those packages plus the Worker implementation, legacy direct adapter, and
`agent.infrastructure.terminal_inspection`. Its
`reports/build.json` records the source commit, pipeline ID, version, filename,
size, SHA-256, Python version, dependency-presence checks, and archive results.
It includes a schema version and an empty forbidden-module match list on
success. The runtime receipt records the candidate hash before/after testing,
Agent principal/session, Worker principal/PID/SID/session/protocol, terminal
principal/PID/SID/session/path/build, runtime state, three read-success flags,
and final health. For account information it records only success and field
count; the returned values are never written to the evidence file.

The Windows no-MT5 jobs verify that the candidate's Worker-aware diagnostics
remain usable and that the Agent can stay alive in a degraded state when no
Worker is available. They do not require or inspect a local MT5 installation.

The MT5 integration job downloads that exact candidate and evidence. It checks
the dedicated Worker task, configured principals, Session 0 caller, nonzero
Worker session, authenticated pipe handshake, and protocol version. It starts
the candidate Agent and exercises the application HTTP command path for health,
`mt5.get_symbols_total`, `mt5.get_terminal_version`, and
`mt5.get_account_information`. Account values are held only in memory; evidence
stores a success flag and field count. It independently checks terminal owner,
SID, session, and executable path. CI stops only the temporary candidate Agent;
it does not stop the persistent Worker or terminal.

The MT5 gate verifies the candidate hash before and after its smoke sequence.
The final package gate checks the build, control-plane, and runtime evidence for
matching pipeline ID, commit, version, filename, and SHA-256. It writes
`sha256.txt` and release evidence without rebuilding. The release candidate
must therefore be the same binary built, tested, and runtime-validated:
**BUILD ONCE → TEST SAME ARTIFACT → RELEASE SAME ARTIFACT**. The package job
validates receipts and packages evidence; it does not rebuild the executable.

Workflow rules retain the existing behavior for stable semantic-version tags,
merge requests, manual branch pipelines, and pushes to develop/staging/main.
An open merge request suppresses duplicate branch push pipelines. The ACL
experiment remains source tooling but is not a mandatory release dependency.
No CI job creates a tag or publishes a release.

## Local validation

On Linux, install `requirements-dev.txt` into a disposable environment or
job-local target, then run the portable checks:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m compileall -q agent main.py
python3 -m pytest -q --ignore=tests/test_windows_worker_launcher.py
```

On Windows, use a clean environment without MetaTrader5 for Agent validation
and build. The normal CI release evidence is generated by the Windows build and
smoke jobs; a local direct PyInstaller build is not a substitute for matching
build/runtime receipts.

The separate Worker environment is provisioned from
`requirements-mt5-worker.txt`. Do not install it into the Agent build
environment.

## Configuration validation and live pipeline

Before using a new CI revision, validate the YAML with GitLab CI Lint and then
run the pipeline on a commit containing that revision. Local YAML parsing and
PowerShell/evidence tests cannot prove Runner scheduling, artifact transfer,
or the cold machine's live Runtime Worker state. The first live pipeline is
required to accept the topology. The pipeline must fail closed on provenance
mismatch or missing Worker/runtime evidence; it must not repair
Autologon, accounts, tasks, pipe ACLs, or the Windows host.
