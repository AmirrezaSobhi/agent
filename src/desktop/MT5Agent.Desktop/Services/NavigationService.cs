using System;
using System.Collections.Generic;
using MT5Agent.Desktop.ViewModels;

namespace MT5Agent.Desktop.Services
{
    public sealed class NavigationService : ViewModelBase
    {
        private readonly Dictionary<string, Func<ViewModelBase>> _routes = new Dictionary<string, Func<ViewModelBase>>(StringComparer.OrdinalIgnoreCase);
        private ViewModelBase _currentViewModel;
        private string _currentRoute;

        public ViewModelBase CurrentViewModel { get { return _currentViewModel; } private set { SetProperty(ref _currentViewModel, value); } }
        public string CurrentRoute { get { return _currentRoute; } private set { SetProperty(ref _currentRoute, value); } }

        public void Register(string route, Func<ViewModelBase> factory)
        {
            if (string.IsNullOrWhiteSpace(route)) throw new ArgumentException("A route is required.", "route");
            if (factory == null) throw new ArgumentNullException("factory");
            if (_routes.ContainsKey(route)) throw new InvalidOperationException("Route is already registered.");
            _routes.Add(route, factory);
        }

        public void Navigate(string route)
        {
            Func<ViewModelBase> factory;
            if (!_routes.TryGetValue(route ?? string.Empty, out factory)) throw new ArgumentOutOfRangeException("route", "Unknown navigation route.");
            if (string.Equals(CurrentRoute, route, StringComparison.OrdinalIgnoreCase)) return;
            var next = factory();
            var previous = CurrentViewModel;
            CurrentViewModel = next;
            CurrentRoute = route;
            if (previous != null) previous.Dispose();
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing && CurrentViewModel != null)
            {
                CurrentViewModel.Dispose();
                CurrentViewModel = null;
            }
            base.Dispose(disposing);
        }
    }
}
