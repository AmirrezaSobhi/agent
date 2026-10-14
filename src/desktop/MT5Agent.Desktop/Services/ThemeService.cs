using System;
using System.Linq;
using System.Windows;

namespace MT5Agent.Desktop.Services
{
    public interface IThemeService
    {
        ThemePreference CurrentTheme { get; }
        void Apply(ThemePreference theme);
    }

    public sealed class ThemeService : IThemeService
    {
        private readonly Application _application;
        private ResourceDictionary _activeDictionary;

        public ThemeService(Application application)
        {
            if (application == null) throw new ArgumentNullException("application");
            _application = application;
        }

        public ThemePreference CurrentTheme { get; private set; }

        public void Apply(ThemePreference theme)
        {
            var dictionaries = _application.Resources.MergedDictionaries;
            var target = new ResourceDictionary
            {
                Source = new Uri(theme == ThemePreference.Dark
                    ? "/MT5Agent.Desktop;component/Themes/Colors.Dark.xaml"
                    : "/MT5Agent.Desktop;component/Themes/Colors.Light.xaml", UriKind.Relative)
            };

            if (_activeDictionary != null) dictionaries.Remove(_activeDictionary);
            else
            {
                var existing = dictionaries.FirstOrDefault(item => item.Source != null &&
                    (item.Source.OriginalString.EndsWith("Colors.Dark.xaml", StringComparison.OrdinalIgnoreCase) ||
                     item.Source.OriginalString.EndsWith("Colors.Light.xaml", StringComparison.OrdinalIgnoreCase)));
                if (existing != null) dictionaries.Remove(existing);
            }
            dictionaries.Insert(0, target);
            _activeDictionary = target;
            CurrentTheme = theme;
        }
    }
}
