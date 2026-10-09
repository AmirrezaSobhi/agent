# MT5Agent Desktop v0.1.5 — Windows x64

## Prerequisites

- Windows 10 x64, Windows 11 x64, or Windows Server 2022/2025 x64 with Desktop
  Experience. Windows 11 and Windows Server validation remains
  `DEFERRED — PRODUCT OWNER VALIDATION` for this phase.
- Microsoft .NET Framework 4.8 or later runtime. The Developer/Targeting Pack
  and Visual Studio/MSBuild are build-machine prerequisites only.
- An already installed and provisioned MT5Agent Python Agent/Runtime. It is
  managed separately and is not included here. The Desktop app can start while
  the Agent is offline.

Server Core is unsupported because this is a WPF desktop application.

## First install

1. Verify the archive SHA-256 against the value supplied with the artifact and
   verify the extracted `SHA256SUMS.txt` using the bundled package verifier or
   Windows `Get-FileHash`.
2. Extract the archive to a versioned per-user directory such as
   `%LOCALAPPDATA%\Programs\MT5Agent\Desktop\v0.1.5`. No administrator rights
   are required for this location.
3. Start `app\MT5Agent.Desktop.exe`. Create a shortcut if desired.
4. If the Agent is provisioned, its machine administrator must separately
   configure the Management Pipe allowlist. The UI never falls back to `/command`
   or connects to the Worker pipe.

The Dashboard queries and controls only the fixed Windows Service name
`MT5Agent` through the Windows Service Control Manager. The user's existing
Windows token and the Service's configured SCM ACL determine query/start/stop
rights. Stop and restart ask for confirmation. The app never elevates, changes
Service ACLs, uses `/command`, or starts arbitrary processes. An absent Service
is reported as Not Installed. This ZIP does not create or install a Service,
change machine configuration, provision an account, configure Autologon,
install MT5, or authorize trading.

## Upgrade and rollback

1. Exit the Desktop application before replacing or removing files.
2. Extract a new version into a new versioned directory. Keep the previous
   directory until the new version has been checked.
3. Repoint the user shortcut to the new executable. User preferences remain in
   `%LOCALAPPDATA%\MT5Agent\Desktop\preferences.v1`, outside the app folder.
4. If the new version fails, exit it and point the shortcut back to the previous
   directory. This is a manual rollback; no updater or automatic migration is
   included.

Never extract over the running executable. This package does not change Agent,
Worker, MT5, machine configuration, or existing user preferences.

## Removal

Exit the Desktop application, remove its shortcut, and delete only the versioned
Desktop application directory. Keep the per-user preferences and any Agent
configuration/logs unless the user separately chooses to remove them. No Service
or Runtime uninstall action is performed by this package.
