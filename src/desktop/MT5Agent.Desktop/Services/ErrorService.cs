using System;
using MT5Agent.Desktop.ViewModels;

namespace MT5Agent.Desktop.Services
{
    public interface IErrorHandler
    {
        void Handle(Exception exception, string context);
        void Clear();
    }

    public sealed class ErrorService : ViewModelBase, IErrorHandler
    {
        private string _message;
        private bool _hasError;
        public string Message { get { return _message; } private set { SetProperty(ref _message, value); } }
        public bool HasError { get { return _hasError; } private set { SetProperty(ref _hasError, value); } }

        public void Handle(Exception exception, string context)
        {
            // Exception text is intentionally not surfaced to the user or persisted.
            Message = Resources.Strings.OperationError;
            HasError = true;
        }

        public void Clear() { Message = null; HasError = false; }
    }
}
