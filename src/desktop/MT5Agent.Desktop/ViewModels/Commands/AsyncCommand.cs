using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Input;
using MT5Agent.Desktop.Services;

namespace MT5Agent.Desktop.ViewModels.Commands
{
    public sealed class AsyncCommand : ICommand, IDisposable
    {
        private readonly Func<CancellationToken, Task> _execute;
        private readonly IErrorHandler _errors;
        private readonly object _sync = new object();
        private CancellationTokenSource _cancellation;
        private int _running;
        private bool _disposed;

        public AsyncCommand(Func<CancellationToken, Task> execute, IErrorHandler errors)
        {
            if (execute == null) throw new ArgumentNullException("execute");
            if (errors == null) throw new ArgumentNullException("errors");
            _execute = execute;
            _errors = errors;
        }

        public event EventHandler CanExecuteChanged;
        public bool IsRunning { get { return Volatile.Read(ref _running) != 0; } }
        public bool CanExecute(object parameter)
        {
            lock (_sync) return !_disposed && !IsRunning;
        }
        public async void Execute(object parameter) { await ExecuteAsync(CancellationToken.None); }

        public async Task ExecuteAsync(CancellationToken cancellationToken)
        {
            if (Interlocked.CompareExchange(ref _running, 1, 0) != 0) return;
            CancellationTokenSource cancellation;
            lock (_sync)
            {
                if (_disposed)
                {
                    Interlocked.Exchange(ref _running, 0);
                    return;
                }
                cancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                _cancellation = cancellation;
            }
            _errors.Clear();
            RaiseCanExecuteChanged();
            try { await _execute(cancellation.Token); }
            catch (OperationCanceledException) { }
            catch (Exception ex) { _errors.Handle(ex, "AsyncCommand"); }
            finally
            {
                lock (_sync)
                {
                    if (ReferenceEquals(_cancellation, cancellation)) _cancellation = null;
                }
                cancellation.Dispose();
                Interlocked.Exchange(ref _running, 0);
                RaiseCanExecuteChanged();
            }
        }

        public void Cancel()
        {
            lock (_sync)
            {
                var cancellation = _cancellation;
                if (cancellation != null && !cancellation.IsCancellationRequested) cancellation.Cancel();
            }
        }

        public void RaiseCanExecuteChanged()
        {
            var handler = CanExecuteChanged;
            if (handler != null) handler(this, EventArgs.Empty);
        }

        public void Dispose()
        {
            lock (_sync)
            {
                if (_disposed) return;
                _disposed = true;
                var cancellation = _cancellation;
                if (cancellation != null && !cancellation.IsCancellationRequested) cancellation.Cancel();
            }
            RaiseCanExecuteChanged();
        }
    }
}
