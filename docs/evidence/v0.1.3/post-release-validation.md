# v0.1.3 post-release validation

This record separates the official release acceptance from validation that ran
after publication. The release facts were checked against authenticated GitLab
Release, tag, pipeline, job, and Package Registry API responses on 2026-10-08.

## Release acceptance — Pipeline #16

The official GitLab Release `v0.1.3` was published on 2026-10-06 at 02:58:30
UTC. Tag `v0.1.3` resolves to commit
`970c04712853295fd065094b11a2bd541b5a9db8`. [Pipeline #16](http://gitlab.local/root/agent/-/pipelines/16)
ran on that tag and commit and passed all eight release gates. The release
package was produced by [Job #125](http://gitlab.local/root/agent/-/jobs/125).

The official artifact is `MT5Agent-v0.1.3.exe`, 8,124,497 bytes, SHA-256
`175ff421e06d0c7394721dcf2aaa9509b953bc3d9c3d8d7f6fab7afb01e4ab28`. The
Generic Package Registry contains `mt5-agent` version `0.1.3`; its file metadata
and `SHA256SUMS.txt` agree on this hash. See the
[release notes](../../releases/v0.1.3-release-notes.md).

## Post-release validation — Pipeline #17

[Pipeline #17](http://gitlab.local/root/agent/-/pipelines/17) ran on `develop`
at commit `2e01ff78c447d5242e0d582944c43f0d952b3446`. Its final status was
success, and its eight required jobs completed successfully:

| Job | Name | Final status |
|---:|---|---|
| [#126](http://gitlab.local/root/agent/-/jobs/126) | `validate:windows` | success |
| [#127](http://gitlab.local/root/agent/-/jobs/127) | `test:linux` | success |
| [#128](http://gitlab.local/root/agent/-/jobs/128) | `test:windows` | success |
| [#129](http://gitlab.local/root/agent/-/jobs/129) | `build:windows` | success |
| [#130](http://gitlab.local/root/agent/-/jobs/130) | `smoke:invalid-configuration` | success |
| [#131](http://gitlab.local/root/agent/-/jobs/131) | `smoke:control-plane` | success |
| [#134](http://gitlab.local/root/agent/-/jobs/134) | `smoke:mt5-runtime` | success |
| [#133](http://gitlab.local/root/agent/-/jobs/133) | `package:windows` | success |

### MT5 runtime smoke history

The first MT5 runtime smoke execution, [Job #132](http://gitlab.local/root/agent/-/jobs/132),
failed with `script_failure` and exit status 1. Its trace records a PowerShell
exception; the expected `reports/mt5-runtime.json` was not produced. The trace
does not establish the root cause.

The later execution, [Job #134](http://gitlab.local/root/agent/-/jobs/134),
succeeded. Its runtime report records `status: PASS` and `runtime_state:
MT5_CONNECTED`; Agent ran in Session 0, and the Worker and MT5 terminal ran in
Session 1. The three safe reads—symbols total, terminal version, and account
information—succeeded. The report retained only account-information success
and field count, not account values.

The Windows reboot and manual retry are operational observations. The GitLab
API confirms the failed and successful Job records, but does not independently
prove that reboot occurred or establish it as the cause of recovery. Do not
attribute the initial failure to a startup-timing defect without further
evidence, and do not mark Worker startup reliability as resolved on this basis.

## Scope

Pipeline #17 is post-release validation on `develop`; it is not the original
release pipeline and does not change the provenance of the published v0.1.3
binary. Pipeline #11 remains historical Phase 4D candidate evidence in
[its original record](phase4d-live-ci-acceptance.md).
