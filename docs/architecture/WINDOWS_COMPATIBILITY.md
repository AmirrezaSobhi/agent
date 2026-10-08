# Windows Compatibility Matrix

**Status:** Phase 5 inventory; product matrix is approved, but compatibility is
not yet verified for all approved operating systems. Compilation on Windows 10
does not establish runtime compatibility on other Windows releases.

## Approved Commercial Matrix

| Operating system | Desktop requirement | Available Phase 5 evidence | Compatibility result |
|---|---|---|---|
| Windows 10 x64 | Interactive desktop; supported servicing/build policy still needs definition | Windows 10 Pro 22H2 x64 inventory and prior Phase 4 build/UIA evidence; Phase 5 interactive revalidation unavailable | Partial evidence; not Phase 5 verified |
| Windows 11 x64 | Interactive desktop | No authorized Windows 11 test host identified | Pending |
| Windows Server 2022 x64 | Desktop Experience only; Server Core unsupported | No test host identified | Pending |
| Windows Server 2025 x64 | Desktop Experience only; Server Core unsupported | No test host identified | Pending |

Windows 7 is legacy Runtime testing only and is not a commercial Desktop Client
target. Windows 8/8.1, Windows Server 2012/2012 R2/2016/2019, Server Core, and
all other Windows versions are outside the approved support matrix.

## Phase 5 Environment Inventory

Read-only discovery on 2026-10-08 identified two Windows 10 x64 hosts:

| Host alias | OS / session | .NET / build tools | Runner and Agent state | Phase 5 suitability |
|---|---|---|---|---|
| `win10-runner` (`window10-test`) | Windows 10 Pro build 19045 x64; active console user `Administrator`, session 1 | .NET Framework Release registry value `0x8234d`; official 4.8 targeting pack and MSBuild `4.8.9037.0` were evidenced in Phase 4 | `gitlab-runner` service is Running/Automatic as LocalSystem. No MT5Agent Agent Service was found. Runner config does not define `MT5_AGENT_WORKER_PRINCIPAL` or `MT5_AGENT_ACL_EXPERIMENT`. | Session 0 ACL experiment can be considered through the dedicated fail-closed CI test with explicit pipeline-only variables; no installed Agent-Service validation. |
| `win10-mt5-runner` | Windows 10 Pro build 19045 x64; active console user `mt5runtimeuser`, session 1 | Not fully inventoried in Phase 5 | GitLab Runner is Running as `.\Administrator`; Python and `terminal64` processes are present in session 1. No MT5Agent Agent Service was found. | Do not alter existing Runtime processes/account. Runtime process presence is not installed-Service evidence. |

No Windows 11, Windows Server 2022 Desktop Experience, or Windows Server 2025
Desktop Experience host was present in the authorized runner inventory. No VM,
disk, snapshot, account, or host configuration was created or changed. The
interactive desktop is available on the Windows 10 hosts, but no Phase 5
application launch or screenshot was captured in this environment.

## Technical Compatibility vs. Microsoft Lifecycle

The product matrix above is a Product Owner decision. Compatibility must be
proven by package launch, interactive behavior, Service/Runtime integration,
and the applicable tests on each OS; framework support statements alone are
insufficient.

Microsoft lifecycle is a separate operational risk. As of the references
reviewed on 2026-10-08, Windows 10 Home/Pro 22H2 reached end of support on
2025-10-14; eligible editions/programs may have separate ESU terms. Windows
Server 2022 Mainstream Support ends 2026-10-13 and Extended Support ends
2031-10-14. Windows Server 2025 Mainstream Support ends 2029-11-13 and
Extended Support ends 2034-11-14. Windows 11 servicing is release-specific;
the product must test and support only feature releases still receiving
security updates. Recheck these lifecycle dates and edition/build policy at
each release.

Sources: [Windows 10 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-10-home-and-pro),
[Windows Server 2022 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-server-2022),
[Windows Server 2025 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-server-2025),
[Windows 11 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-11-home-and-pro),
[Windows Server installation options](https://learn.microsoft.com/en-us/windows-server/get-started/install-options-server-core-desktop-experience).

## Required Evidence for Each Matrix Row

Before claiming a row verified, capture the OS edition/build/architecture,
.NET Framework release value, display/session type, artifact commit and SHA-256,
interactive launch and screen evidence, application/Service/Runtime results,
test report, and known limitations. Server rows must explicitly confirm Desktop
Experience. Do not substitute one OS row's evidence for another.
