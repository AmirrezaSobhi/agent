using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using System.Windows.Forms;

namespace MT5Agent.Desktop.Services
{
    public interface IDesktopNotifier
    {
        void ConnectionChanged(bool connected);
    }

    public sealed class TrayService : IDisposable, IDesktopNotifier
    {
        private readonly NotifyIcon _icon;
        private readonly IUserPreferencesStore _preferences;
        private readonly Dispatcher _dispatcher;
        private Window _window;
        private DateTime _lastNoticeUtc = DateTime.MinValue;
        private bool _disposed;
        public event EventHandler ExitRequested;

        public TrayService(IUserPreferencesStore preferences, Dispatcher dispatcher)
        {
            _preferences = preferences;
            _dispatcher = dispatcher;
            _icon = new NotifyIcon { Icon = CreateIcon(), Text = "MT5Agent Desktop", Visible = true };
            var menu = new ContextMenuStrip();
            var open = menu.Items.Add("Open MT5Agent");
            open.Click += (sender, args) => _dispatcher.BeginInvoke(new Action(ShowWindow));
            menu.Items.Add(new ToolStripSeparator());
            var exit = menu.Items.Add("Exit");
            exit.Click += (sender, args) => _dispatcher.BeginInvoke(new Action(() =>
            { var handler = ExitRequested; if (handler != null) handler(this, EventArgs.Empty); }));
            _icon.ContextMenuStrip = menu;
            _icon.DoubleClick += (sender, args) => _dispatcher.BeginInvoke(new Action(ShowWindow));
        }

        public bool IsAvailable { get { return !_disposed; } }
        public void Attach(Window window) { _window = window; }
        public void ShowWindow()
        {
            if (_disposed || _window == null) return;
            if (_window.WindowState == WindowState.Minimized) _window.WindowState = WindowState.Normal;
            _window.Show(); _window.Activate();
        }

        public void HideWindow()
        {
            if (!_disposed && _window != null) _window.Hide();
        }

        public void ConnectionChanged(bool connected)
        {
            if (_disposed || !_preferences.Load().NotificationsEnabled || !_icon.Visible) return;
            var now = DateTime.UtcNow;
            if (now - _lastNoticeUtc < TimeSpan.FromSeconds(30)) return;
            _lastNoticeUtc = now;
            _icon.ShowBalloonTip(3500, "MT5Agent", connected ? "Agent connection restored." : "Agent connection lost.",
                connected ? ToolTipIcon.Info : ToolTipIcon.Warning);
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;
            _icon.Visible = false;
            _icon.Dispose();
            _window = null;
        }

        private static Icon CreateIcon()
        {
            var visual = new DrawingVisual();
            using (var context = visual.RenderOpen())
            {
                context.DrawRoundedRectangle(new SolidColorBrush(System.Windows.Media.Color.FromRgb(40, 104, 235)), null,
                    new Rect(0, 0, 64, 64), 16, 16);
                var text = new FormattedText("M", System.Globalization.CultureInfo.InvariantCulture,
                    System.Windows.FlowDirection.LeftToRight, new Typeface("Segoe UI"), 40, System.Windows.Media.Brushes.White,
                    VisualTreeHelper.GetDpi(visual).PixelsPerDip);
                context.DrawText(text, new System.Windows.Point(9, 6));
            }
            var bitmap = new RenderTargetBitmap(64, 64, 96, 96, PixelFormats.Pbgra32);
            bitmap.Render(visual);
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using (var stream = new System.IO.MemoryStream())
            {
                encoder.Save(stream); stream.Position = 0;
                using (var image = new Bitmap(stream))
                {
                    var handle = image.GetHicon();
                    try { return (Icon)Icon.FromHandle(handle).Clone(); }
                    finally { DestroyIcon(handle); }
                }
            }
        }

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool DestroyIcon(IntPtr handle);
    }
}
