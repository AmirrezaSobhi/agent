# WPF Solution and Desktop Engineering Design

**Decision:** C#, WPF, XAML, .NET Framework 4.8, MVVM. Product Owner-approved
and binding for v0.1.4. Python Agent and Python Runtime Worker remain unchanged
operational components. The initial two-project foundation is implemented at
[`src/desktop`](../../src/desktop/README.md); secure IPC and live status remain
planned.

## Recommended solution shape

```text
src/desktop/
├── MT5Agent.Desktop.sln
├── MT5Agent.Desktop/
│   ├── App.xaml
│   ├── Views/
│   ├── ViewModels/
│   ├── Services/
│   │   └── Management/       # IManagementClient + Named Pipe client
│   ├── Controls/
│   ├── Themes/
│   ├── Resources/            # localization and image dictionaries
│   └── Assets/
└── MT5Agent.Desktop.Tests/
    ├── ViewModels/
    ├── Services/
    └── Contracts/
```

Start with **two projects**: the WPF executable and a .NET Framework 4.8 test
project. Keep protocol DTOs, the `IManagementClient` abstraction, serializer,
and future IPC implementation inside the Desktop project under
`Services/Management`.
Tests substitute `IManagementClient` with a fake and run protocol tests against
language-neutral JSON fixtures. A third `Desktop.Contracts` project is not
justified until a second C# consumer or independently versioned shared C# API
exists. Do not put Python implementation details in C# contracts.

### References and dependency direction

- `MT5Agent.Desktop` owns WPF `Views`, `ViewModels`, navigation, composition,
  presentation models, and the management transport adapter.
- `MT5Agent.Desktop.Tests` references `MT5Agent.Desktop` and test framework only.
- Within Desktop, Views bind to ViewModels; ViewModels depend on narrow
  interfaces (`IManagementClient`, `IClock`, `INavigationService`,
  `IUserPreferencesStore`); implementations live in Services. Services do not
  reference Views/ViewModels.
- Python Agent remains a separate executable/repository language boundary
  connected only by the proposed management IPC contract.
- Avoid service-locator, mediator, generic repository, and plugin frameworks.

## MVVM conventions

- Views contain layout, styles, and accessibility metadata; no business or
  transport logic in code-behind. Code-behind may only initialize controls or
  bridge platform lifecycle events into an injected service.
- ViewModels expose bindable immutable/snapshot state, `ICommand` actions and
  validation messages. Async actions use an async command implementation that
  prevents duplicate submission and supports `CancellationToken`.
- Do not expose raw exceptions or secrets to bindings. Convert expected errors
  to typed UI states; send sanitized diagnostics through an injected logger.
- Prefer ordinary POCO ViewModels with `INotifyPropertyChanged`; avoid adding
  MVVM toolkit dependencies for the first release.

## Composition, async, navigation, and resource lifetime

- Use a small manual composition root in `App.OnStartup`: construct config,
  local stores, logger, `NamedPipeManagementClient`, view models and shell.
  This is sufficient DI for two projects and avoids a container dependency.
- All I/O, pipe connect/read/write, service-status probes, log reads, and
  diagnostics collection run asynchronously off the UI thread. Never block on
  `.Result`, `.Wait()`, synchronous dispatcher invocation, or sleep in UI code.
- Use `Dispatcher` only to publish completed state to WPF-bound properties;
  do not dispatch long work. Observe and handle every task exception.
- Use one shell `ContentControl` with a small typed navigation service and
  reusable pages/ViewModels. Preserve page state only where useful. Pages
  subscribe/unsubscribe to events with explicit `IDisposable` lifetime; prefer
  weak events only for framework events whose publisher outlives a page.
- Dispose pipe streams, timers, cancellation sources, file handles and
  notification icon. On shutdown cancel polling, await bounded worker
  completion, unsubscribe events and dispose services. UI shutdown does not
  request Agent or Worker shutdown.
- Background status polling: one in-flight refresh, five-second default poll,
  cancel previous refresh on navigation/manual refresh, exponential reconnect
  backoff with cap; stale threshold is defined in
  [IPC and Status Contract](IPC_CONTRACT.md).

## Localization and UI thread safety

Put all user-visible text in `.resx` resources, use invariant protocol/error
codes internally, and format dates/numbers through current UI culture. English
is the initial resource. Set layout direction from localization resources, not
hard-coded left/right margins; test mixed-direction IDs and numeric values
before adding Persian. WPF `Dispatcher` owns all bound mutable state. Avoid
sharing mutable observable collections across threads; copy/snapshot on
background workers and publish one update.

## UI library evaluation

| Strategy | .NET Framework 4.8 / license | Maintenance, performance, packaging | Decision |
|---|---|---|---|
| Pure/custom WPF | Built-in WPF/XAML; no third-party UI license | Lowest dependency, attack-surface and packaging cost; no additional assembly load. Requires a disciplined token/control-style system and more in-house design work. | **Preferred for v0.1.4.** Use stock WPF controls, custom ResourceDictionaries, and `WindowChrome`/standard Window. |
| MahApps.Metro | Project states .NET Framework 4.6.2+; MIT. Its 2.4 line supports .NET Framework 4.5.2+; 3.0 is a release candidate targeting .NET Framework 4.6.2 plus newer .NET. | Active ecosystem, useful window chrome and theme primitives; adds package/transitive dependencies and style behavior to regression-test. Do not adopt 3.0 RC for release. | Do not add initially. Reconsider only if a small prototype shows a material UX benefit; pin a stable net48-compatible release and review its dependency/license inventory. |
| FluentWPF (`sourcechord/FluentWPF`) | NuGet 0.10.2 includes `net45`; repository is MIT licensed. | Contains Fluent effects/control styles, but package page shows last update 2021-10-10. Older dependency and Windows visual-effect behavior increase maintenance/compatibility risk; additional package/resource dictionaries. | Not selected for initial client. |

Research links (checked 2026-10-08): [Microsoft .NET Framework install/support](https://learn.microsoft.com/en-us/dotnet/framework/install/), [MahApps.Metro](https://github.com/MahApps/MahApps.Metro), [FluentWPF NuGet](https://www.nuget.org/packages/FluentWPF/0.10.2), and [FluentWPF source/license](https://github.com/sourcechord/FluentWPF).

## WPF Design System

Create centralized XAML dictionaries: `Colors.Light.xaml`, `Colors.Dark.xaml`,
`Typography.xaml`, `Spacing.xaml`, `Controls.xaml`, and `States.xaml`. Views must
not hard-code colors, spacing, or typography. Proposed initial tokens:

| Token | Light | Dark | Use |
|---|---|---|---|
| `Color.Canvas` | `#F6F8FB` | `#111827` | App background |
| `Color.Surface` | `#FFFFFF` | `#1F2937` | Cards/navigation |
| `Color.SurfaceAlt` | `#EEF2F7` | `#273449` | Inputs/hover |
| `Color.TextPrimary` | `#172033` | `#F3F4F6` | Main text |
| `Color.TextSecondary` | `#475569` | `#CBD5E1` | Secondary text |
| `Color.Accent` | `#155EEF` | `#8AB4FF` | Primary action/focus |
| `Color.Success` | `#137A45` | `#65D69A` | Positive state |
| `Color.Warning` | `#8A5200` | `#FFC857` | Warning |
| `Color.Error` | `#B42318` | `#FF8A80` | Error |
| `Color.Border` | `#D5DCE7` | `#3B475A` | Dividers/borders |

Typography: Segoe UI UI font stack; body 14 px, secondary 12 px, section 18 px,
page title 24 px; allow Windows text scaling and avoid fixed-height text rows.
Spacing: 4/8/12/16/24/32 px scale. Controls: 32 px compact / 40 px normal
minimum height, 8 px card radius, 1 px border, clear focus ring, consistent
icons, labels and disabled states. These are starting tokens and must pass
contrast/usability review; color alone never conveys state.

Dark/light selection is a per-user preference; start from OS theme only on
first run. Support window resize from 800×600 logical pixels through maximized
layout; at narrow widths collapse sidebar to icon/overlay mode and stack cards.
Use DPI-aware WPF manifests, layout rounding and size-to-content only for
dialogs; test 100%, 125%, 150%, 200% scale and multi-monitor DPI transitions.

## Shell and module presentation

Desktop Shell: title bar with product/build identity and window controls;
left sidebar with Dashboard, Runtime, Accounts, Security, Settings, Logs,
Diagnostics, Updates, Support, About; main content area; optional status/footer
with last refresh time. Hide or label unavailable modules as “Not available in
this release”; never render mocked live values.

Dashboard cards: Service, local Agent, Worker, MT5 connection, central
connection, and trading capability/authorization. Cards are reorderable and
visible cards/width are per-user preferences; machine defaults seed first run;
future cloud sync is deferred. Account contents stay hidden if identity or
permission is unresolved.

## System Tray and notifications

Use the framework-provided `System.Windows.Forms.NotifyIcon` only if the
prototype demonstrates reliable interop and clean disposal; otherwise use a
small, reviewed Win32 notification-area wrapper. Keep the tray object and UI in
the same user-session process. Menu actions: Open, Refresh, Exit UI; Service
actions require the separate authorization/SCM path. Closing to tray is a
per-user preference; exiting UI never stops Service/Worker. Windows toast
notifications are optional and may be unsupported in some server/session
contexts; tray/notification failure cannot affect safety controls.

## UX state requirements

- Loading: skeleton/progress and cancellable work; never block window creation.
- Empty: plain explanation plus only actions available to current user.
- Stale: last successful state, observation timestamp and age, visibly stale.
- Offline: distinct local Service offline, pipe unavailable, and central offline.
- Error: stable error code, plain description, correlation ID and permitted
  recovery guidance. Do not disclose stack traces, tokens or rejected secret data.
- Unavailable/unsupported: explicit for central connectivity in Local Setup and
  trading capability in this release; do not show “disabled” as if a control
  exists when the feature is not implemented.

## Related documents

[ADR-ARCH-015](adr/ADR-ARCH-015-wpf-technology.md) ·
[IPC and Status Contract](IPC_CONTRACT.md) ·
[Quality Gates](QUALITY_GATES.md) · [Implementation Plan](IMPLEMENTATION_PLAN.md)
