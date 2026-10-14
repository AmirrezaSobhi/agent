using System;

namespace MT5Agent.Desktop.Services
{
    public sealed class ManagementIpcException : Exception
    {
        public ManagementIpcException(string code) : base(code) { Code = code; }
        public ManagementIpcException(string code, Exception inner) : base(code, inner) { Code = code; }
        public string Code { get; private set; }
    }
}
