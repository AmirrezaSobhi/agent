// Test-only probe for an isolated Windows Phase 5 Management Pipe DACL test.
// It reports the caller token and native CreateFile result. It never sends
// caller identity claims and never performs a management operation.
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;

public static class Phase5ManagementPipeDaclProbe
{
    private const string PipePath = @"\\.\pipe\MT5Agent.Management.v1";
    private const uint GenericRead = 0x80000000;
    private const uint GenericWrite = 0x40000000;
    private const uint ReadControl = 0x00020000;
    private const uint OpenExisting = 3;
    private static readonly IntPtr InvalidHandle = new IntPtr(-1);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateFile(string name, uint access, uint share,
        IntPtr security, uint creation, uint flags, IntPtr template);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr handle);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool LogonUser(string user, string domain, string password,
        int logonType, int logonProvider, out IntPtr token);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool ImpersonateLoggedOnUser(IntPtr token);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool RevertToSelf();

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool GetTokenInformation(IntPtr token, int informationClass,
        out uint information, uint informationLength, out uint returnLength);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern uint GetSecurityInfo(IntPtr handle, int objectType,
        uint information, out IntPtr owner, out IntPtr group, out IntPtr dacl,
        out IntPtr sacl, out IntPtr securityDescriptor);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertSecurityDescriptorToStringSecurityDescriptor(
        IntPtr securityDescriptor, uint revision, uint information,
        out IntPtr sddl, out uint sddlLength);

    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr memory);

    private static string ReadPipeDacl(IntPtr pipe)
    {
        IntPtr owner, group, dacl, sacl, descriptor;
        // Named Pipe handles may be exposed as file or kernel objects by the
        // Windows version. Try the file-object classification first.
        uint result = GetSecurityInfo(pipe, 1, 0x4, out owner, out group,
            out dacl, out sacl, out descriptor);
        if (result != 0)
        {
            uint fileError = result;
            result = GetSecurityInfo(pipe, 6, 0x4, out owner, out group,
                out dacl, out sacl, out descriptor);
            if (result != 0) return "GetSecurityInfoFileError=" + fileError +
                ";GetSecurityInfoKernelError=" + result;
        }
        IntPtr sddl;
        uint length;
        try
        {
            if (!ConvertSecurityDescriptorToStringSecurityDescriptor(
                descriptor, 1, 0x4, out sddl, out length))
                return "ConvertSddlError=" + Marshal.GetLastWin32Error();
            try { return Marshal.PtrToStringUni(sddl); }
            finally { LocalFree(sddl); }
        }
        finally { LocalFree(descriptor); }
    }

    private static int Main()
    {
        string[] args = Environment.GetCommandLineArgs();
        if (args.Length > 1 && args[1] == "--impersonate")
            return ProbeAsStandardUser(Console.ReadLine(), Console.ReadLine(), Console.ReadLine());

        using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
        {
            Console.WriteLine("identity=" + identity.Name);
            Console.WriteLine("caller_sid=" + (identity.User == null ? "UNKNOWN" : identity.User.Value));
            Console.WriteLine("session_id=" + Process.GetCurrentProcess().SessionId);
            Console.WriteLine("pid=" + Process.GetCurrentProcess().Id);
        }

        IntPtr pipe = CreateFile(PipePath, GenericRead | GenericWrite | ReadControl, 0,
            IntPtr.Zero, OpenExisting, 0, IntPtr.Zero);
        if (pipe == InvalidHandle)
        {
            int error = Marshal.GetLastWin32Error();
            Console.WriteLine("layer=CreateFile/WindowsPipeDACL");
            Console.WriteLine("outcome=connection_denied");
            Console.WriteLine("win32_error=" + error);
            return error == 5 ? 0 : 2;
        }

        try
        {
            Console.WriteLine("layer=CreateFile/WindowsPipeDACL");
            Console.WriteLine("outcome=pipe_opened");
            Console.WriteLine("pipe_sddl=" + ReadPipeDacl(pipe));
            return 0;
        }
        finally { CloseHandle(pipe); }
    }

    public static int ProbeAsStandardUser(string domain, string user, string password)
    {
        // Callers supply credentials in memory so the temporary password is
        // absent from the process command line and is never written to output.
        IntPtr token;
        if (!LogonUser(user, domain, password, 2, 0, out token))
        {
            Console.WriteLine("domain=" + domain);
            Console.WriteLine("user=" + user);
            Console.WriteLine("password_length=" + (password == null ? 0 : password.Length));
            Console.WriteLine("layer=LogonUser");
            Console.WriteLine("outcome=logon_failed");
            Console.WriteLine("win32_error=" + Marshal.GetLastWin32Error());
            password = null;
            return 3;
        }

        bool impersonating = false;
        try
        {
            if (!ImpersonateLoggedOnUser(token))
            {
                Console.WriteLine("layer=ImpersonateLoggedOnUser");
                Console.WriteLine("outcome=impersonation_failed");
                Console.WriteLine("win32_error=" + Marshal.GetLastWin32Error());
                return 4;
            }
            impersonating = true;
            using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
            {
                Console.WriteLine("thread_identity=" + identity.Name);
                Console.WriteLine("caller_sid=" + (identity.User == null ? "UNKNOWN" : identity.User.Value));
                uint session;
                uint returned;
                if (GetTokenInformation(identity.Token, 12, out session, 4, out returned))
                    Console.WriteLine("caller_token_session_id=" + session);
                else
                    Console.WriteLine("caller_token_session_error=" + Marshal.GetLastWin32Error());
            }

            IntPtr pipe = CreateFile(PipePath, GenericRead | GenericWrite | ReadControl,
                0, IntPtr.Zero, OpenExisting, 0, IntPtr.Zero);
            if (pipe == InvalidHandle)
            {
                int error = Marshal.GetLastWin32Error();
                Console.WriteLine("layer=CreateFile/WindowsPipeDACL");
                Console.WriteLine("outcome=connection_denied");
                Console.WriteLine("win32_error=" + error);
                return error == 5 ? 0 : 2;
            }

            try
            {
                Console.WriteLine("layer=CreateFile/WindowsPipeDACL");
                Console.WriteLine("outcome=pipe_opened_unexpectedly");
                Console.WriteLine("pipe_sddl=" + ReadPipeDacl(pipe));
                return 5;
            }
            finally { CloseHandle(pipe); }
        }
        finally
        {
            if (impersonating && !RevertToSelf())
                Console.Error.WriteLine("RevertToSelfError=" + Marshal.GetLastWin32Error());
            CloseHandle(token);
            password = null;
        }
    }
}
