using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Pipes;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

namespace MT5Agent.Desktop.Services
{
    /// <summary>Read-only v1 client. It opens only the dedicated Management pipe.</summary>
    public sealed class NamedPipeManagementClient : IManagementClient
    {
        public const string PipeName = "MT5Agent.Management.v1";
        public const int ProtocolVersion = 1;
        public const int MaxMessageBytes = 65536;
        public const int TimeoutMilliseconds = 2000;
        private readonly JavaScriptSerializer _serializer = new JavaScriptSerializer();

        public async Task<ManagementStatus> GetStatusAsync(CancellationToken cancellationToken)
        {
            var requestId = Guid.NewGuid().ToString("D");
            var correlationId = Guid.NewGuid().ToString("D");
            var request = new Dictionary<string, object>
            {
                { "protocol_version", ProtocolVersion }, { "request_id", requestId },
                { "correlation_id", correlationId }, { "operation", "status.get" },
                { "deadline_utc", DateTime.UtcNow.AddMilliseconds(TimeoutMilliseconds).ToString("o", CultureInfo.InvariantCulture) },
                { "payload", new Dictionary<string, object>() }
            };
            var raw = Encoding.UTF8.GetBytes(_serializer.Serialize(request));
            if (raw.Length > MaxMessageBytes) throw new ManagementIpcException("MESSAGE_TOO_LARGE");

            using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken))
            {
                timeout.CancelAfter(TimeoutMilliseconds);
                Exception lastFailure = null;
                for (var attempt = 0; attempt < 3; attempt++)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    var retry = false;
                    try
                    {
                        var status = await SendOnceAsync(raw, requestId, correlationId, timeout.Token).ConfigureAwait(false);
                        cancellationToken.ThrowIfCancellationRequested();
                        return status;
                    }
                    catch (ManagementIpcException ex)
                    {
                        if (ex.Code != "PIPE_BUSY" && ex.Code != "PIPE_NOT_FOUND") throw;
                        lastFailure = ex;
                        retry = true;
                    }
                    catch (OperationCanceledException)
                    {
                        if (cancellationToken.IsCancellationRequested) throw;
                        throw new ManagementIpcException("TIMEOUT");
                    }
                    if (retry && attempt < 2)
                        await Task.Delay(100 * (attempt + 1), timeout.Token).ConfigureAwait(false);
                }
                cancellationToken.ThrowIfCancellationRequested();
                if (timeout.IsCancellationRequested) throw new ManagementIpcException("TIMEOUT");
                throw lastFailure as ManagementIpcException ?? new ManagementIpcException("SERVICE_UNAVAILABLE");
            }
        }

        private async Task<ManagementStatus> SendOnceAsync(byte[] request, string requestId,
            string correlationId, CancellationToken cancellationToken)
        {
            using (var pipe = new NamedPipeClientStream(".", PipeName, PipeDirection.InOut,
                PipeOptions.Asynchronous, TokenImpersonationLevel.Impersonation))
            {
                try
                {
                    var exchange = ExchangeAsync(pipe, request, requestId, correlationId, cancellationToken);
                    var canceled = Task.Delay(Timeout.Infinite, cancellationToken);
                    if (await Task.WhenAny(exchange, canceled).ConfigureAwait(false) != exchange)
                    {
                        pipe.Dispose();
                        ObserveFault(exchange);
                        cancellationToken.ThrowIfCancellationRequested();
                        throw new ManagementIpcException("TIMEOUT");
                    }
                    return await exchange.ConfigureAwait(false);
                }
                catch (ManagementIpcException) { throw; }
                catch (OperationCanceledException) { throw; }
                catch (UnauthorizedAccessException ex) { throw new ManagementIpcException("ACCESS_DENIED", ex); }
                catch (TimeoutException ex) { throw new ManagementIpcException("TIMEOUT", ex); }
                catch (IOException ex)
                {
                    var code = (ex.HResult & 0xffff) == 231 ? "PIPE_BUSY" :
                        (ex.HResult & 0xffff) == 5 ? "ACCESS_DENIED" :
                        (ex.HResult & 0xffff) == 2 ? "PIPE_NOT_FOUND" : "PIPE_BROKEN";
                    throw new ManagementIpcException(code, ex);
                }
            }
        }

        private async Task<ManagementStatus> ExchangeAsync(NamedPipeClientStream pipe, byte[] request,
            string requestId, string correlationId, CancellationToken cancellationToken)
        {
            await pipe.ConnectAsync(TimeoutMilliseconds, cancellationToken).ConfigureAwait(false);
            pipe.ReadMode = PipeTransmissionMode.Message;
            await pipe.WriteAsync(request, 0, request.Length, cancellationToken).ConfigureAwait(false);
            var responseBytes = await ReadMessageAsync(pipe, cancellationToken).ConfigureAwait(false);
            var acknowledgement = Encoding.UTF8.GetBytes(_serializer.Serialize(
                new Dictionary<string, object> { { "ack", requestId } }));
            await pipe.WriteAsync(acknowledgement, 0, acknowledgement.Length, cancellationToken).ConfigureAwait(false);
            return ParseResponse(responseBytes, requestId, correlationId);
        }

        private static void ObserveFault(Task task)
        {
            task.ContinueWith(failed => { var ignored = failed.Exception; }, TaskContinuationOptions.OnlyOnFaulted);
        }

        private static async Task<byte[]> ReadMessageAsync(NamedPipeClientStream pipe, CancellationToken cancellationToken)
        {
            using (var output = new MemoryStream())
            {
                var buffer = new byte[4096];
                do
                {
                    var count = await pipe.ReadAsync(buffer, 0, buffer.Length, cancellationToken).ConfigureAwait(false);
                    if (count == 0) throw new ManagementIpcException("PIPE_BROKEN");
                    if (output.Length + count > MaxMessageBytes) throw new ManagementIpcException("MESSAGE_TOO_LARGE");
                    output.Write(buffer, 0, count);
                } while (!pipe.IsMessageComplete);
                return output.ToArray();
            }
        }

        private ManagementStatus ParseResponse(byte[] bytes, string requestId, string correlationId)
        {
            Dictionary<string, object> envelope;
            try { envelope = _serializer.Deserialize<Dictionary<string, object>>(Encoding.UTF8.GetString(bytes)); }
            catch (Exception ex) { throw new ManagementIpcException("INVALID_RESPONSE", ex); }
            if (envelope == null || IntValue(envelope, "protocol_version") != ProtocolVersion)
                throw new ManagementIpcException("PROTOCOL_MISMATCH");
            if (String.Equals(Text(envelope, "result"), "error", StringComparison.Ordinal) &&
                String.Equals(Text(envelope, "code"), "MESSAGE_TOO_LARGE", StringComparison.Ordinal))
                throw new ManagementIpcException("MESSAGE_TOO_LARGE");
            if (!String.Equals(Text(envelope, "request_id"), requestId, StringComparison.Ordinal) ||
                !String.Equals(Text(envelope, "correlation_id"), correlationId, StringComparison.Ordinal))
                throw new ManagementIpcException("CORRELATION_MISMATCH");
            if (!String.Equals(Text(envelope, "result"), "ok", StringComparison.Ordinal))
                throw new ManagementIpcException(Text(envelope, "code") ?? "INTERNAL_ERROR");
            var data = envelope["data"] as Dictionary<string, object>;
            if (data == null) throw new ManagementIpcException("INVALID_RESPONSE");
            var observed = ParseTimestamp(Text(data, "observed_at_utc") ?? Text(envelope, "observed_at_utc"));
            if (!observed.HasValue) throw new ManagementIpcException("INVALID_RESPONSE");
            var age = DateTime.UtcNow - observed.Value;
            return new ManagementStatus
            {
                AgentState = Text(data, "agent_state") ?? "UNKNOWN",
                WorkerState = Text(data, "worker_state") ?? "UNKNOWN",
                RuntimeState = Text(data, "runtime_state") ?? "UNKNOWN",
                Mt5Connected = BoolValue(data, "mt5_connected"),
                CentralState = Text(data, "central_state") ?? "NOT_CONFIGURED",
                TradingCapability = Text(data, "trading_capability") ?? "UNSUPPORTED",
                TradingAuthorized = Text(data, "trading_authorized") ?? "NOT_AUTHORIZED",
                IsObserved = true, IsStale = age > TimeSpan.FromSeconds(15) || age < TimeSpan.FromMinutes(-5),
                ObservedAtUtc = observed, ErrorCode = "OK", Reason = Text(envelope, "message")
            };
        }

        private static string Text(IDictionary<string, object> data, string key)
        { object value; return data.TryGetValue(key, out value) ? value as string : null; }

        private static int IntValue(IDictionary<string, object> data, string key)
        { object value; return data.TryGetValue(key, out value) ? Convert.ToInt32(value, CultureInfo.InvariantCulture) : -1; }

        private static bool BoolValue(IDictionary<string, object> data, string key)
        { object value; return data.TryGetValue(key, out value) && value is bool && (bool)value; }

        private static DateTime? ParseTimestamp(string value)
        {
            DateTime result;
            if (!DateTime.TryParse(value, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out result)) return null;
            return result;
        }
    }
}
