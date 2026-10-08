# Windows Named Pipe Identity Security Spike

This isolated `.NET Framework 4.8` test validates Windows Named Pipe identity
and DACL primitives. It does not use either MT5Agent production pipe and does
not communicate with the Agent, Worker, MT5 terminal or broker.

The disposable service runs as `LocalSystem` in Session 0 and creates a pipe
with a protected DACL for LocalSystem and one explicitly supplied user SID. It
obtains the caller SID through `NamedPipeServerStream.RunAsClient` and
`WindowsIdentity.GetCurrent(TokenAccessLevels.Query)`. A SID claim in the JSON
request is deliberately forged and must not be trusted. The service verifies
restoration after normal and exceptional impersonation callbacks and fails
closed on an injected identity-capture failure.

Build with the official .NET Framework 4.8 Developer Pack and MSBuild:

```powershell
MSBuild.exe .\WindowsSecuritySpike.csproj /t:Rebuild /p:Configuration=Release /p:Platform=x64 /m:1
```

The integration procedure is Windows-only and must use a disposable runner. It
runs the service as LocalSystem, an authorized client in the logged-on user
session, and an unauthorized test client service as built-in LocalService. It
records session numbers and redacted user SIDs, then removes the service, test
client service, scheduled task, and temporary files in `finally`. It creates
no Windows account. Never run this against a production Agent host or an active
trading machine.

Run `.\run-spike.ps1` from an elevated PowerShell session on a disposable
Windows host with an already logged-on local Administrator session. The script
builds the spike, captures only redacted user SIDs in its evidence output, and
cleans up its temporary Windows services, task and ProgramData directory.
