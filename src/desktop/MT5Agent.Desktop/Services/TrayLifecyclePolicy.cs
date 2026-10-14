namespace MT5Agent.Desktop.Services
{
    /// <summary>Pure window-close policy so tray lifecycle rules remain testable.</summary>
    public static class TrayLifecyclePolicy
    {
        public static bool ShouldHideOnClose(bool explicitExit, bool closeToTray)
        {
            return !explicitExit && closeToTray;
        }
    }
}
