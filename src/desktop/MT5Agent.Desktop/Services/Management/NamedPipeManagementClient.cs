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
            var raw = await RequestAsync("status.get", new Dictionary<string, object>(), cancellationToken).ConfigureAwait(false);
            return ParseStatus(raw);
        }

        public async Task<IList<ManagementLogEntry>> GetLogsAsync(int limit, string severity, CancellationToken cancellationToken)
        {
            if (limit < 1 || limit > 100) throw new ArgumentOutOfRangeException("limit");
            if (severity != "ALL" && severity != "INFO" && severity != "WARNING" && severity != "ERROR")
                throw new ArgumentException("Unsupported severity filter.", "severity");
            var raw = await RequestAsync("logs.query", new Dictionary<string, object>
                { { "limit", limit }, { "severity", severity } }, cancellationToken).ConfigureAwait(false);
            var envelope = DeserializeEnvelope(raw);
            if (!String.Equals(Text(envelope, "result"), "ok", StringComparison.Ordinal))
                throw new ManagementIpcException(Text(envelope, "code") ?? "INTERNAL_ERROR");
            var data = envelope["data"] as IDictionary<string, object>;
            var values = data == null ? null : data["events"] as System.Collections.IList;
            if (values == null || values.Count > limit) throw new ManagementIpcException("INVALID_RESPONSE");
            var entries = new List<ManagementLogEntry>();
            foreach (var item in values)
            {
                var timestamp = ParseTimestamp(ReadText(item, "timestamp_utc"));
                var message = ReadText(item, "message");
                if (!timestamp.HasValue || String.IsNullOrEmpty(message) || message.Length > 256)
                    throw new ManagementIpcException("INVALID_RESPONSE");
                entries.Add(new ManagementLogEntry { TimestampUtc = timestamp.Value,
                    Severity = ReadText(item, "severity") ?? "INFO", Source = ReadText(item, "source") ?? "Agent Management",
                    Code = ReadText(item, "code") ?? "UNKNOWN", Message = message });
            }
            return entries;
        }

        private async Task<byte[]> RequestAsync(string operation, IDictionary<string, object> payload,
            CancellationToken cancellationToken)
        {
            var requestId = Guid.NewGuid().ToString("D");
            var correlationId = Guid.NewGuid().ToString("D");
            var request = new Dictionary<string, object> {
                { "protocol_version", ProtocolVersion }, { "request_id", requestId },
                { "correlation_id", correlationId }, { "operation", operation },
                { "deadline_utc", DateTime.UtcNow.AddMilliseconds(TimeoutMilliseconds).ToString("o", CultureInfo.InvariantCulture) },
                { "payload", payload } };
            var raw = Encoding.UTF8.GetBytes(_serializer.Serialize(request));
            if (raw.Length > MaxMessageBytes) throw new ManagementIpcException("MESSAGE_TOO_LARGE");
            using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken))
            {
                timeout.CancelAfter(TimeoutMilliseconds);
                Exception lastFailure = null;
                for (var attempt = 0; attempt < 3; attempt++)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    try { return await SendOnceAsync(raw, requestId, correlationId, timeout.Token).ConfigureAwait(false); }
                    catch (ManagementIpcException ex)
                    {
                        if (ex.Code != "PIPE_BUSY" && ex.Code != "PIPE_NOT_FOUND") throw;
                        lastFailure = ex;
                    }
                    catch (OperationCanceledException)
                    {
                        if (cancellationToken.IsCancellationRequested) throw;
                        throw new ManagementIpcException("TIMEOUT");
                    }
                    if (attempt < 2) await Task.Delay(100 * (attempt + 1), timeout.Token).ConfigureAwait(false);
                }
                cancellationToken.ThrowIfCancellationRequested();
                if (timeout.IsCancellationRequested) throw new ManagementIpcException("TIMEOUT");
                throw lastFailure as ManagementIpcException ?? new ManagementIpcException("SERVICE_UNAVAILABLE");
            }
        }

        private async Task<byte[]> SendOnceAsync(byte[] request, string requestId,
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

        private async Task<byte[]> ExchangeAsync(NamedPipeClientStream pipe, byte[] request,
            string requestId, string correlationId, CancellationToken cancellationToken)
        {
            await pipe.ConnectAsync(TimeoutMilliseconds, cancellationToken).ConfigureAwait(false);
            pipe.ReadMode = PipeTransmissionMode.Message;
            await pipe.WriteAsync(request, 0, request.Length, cancellationToken).ConfigureAwait(false);
            var responseBytes = await ReadMessageAsync(pipe, cancellationToken).ConfigureAwait(false);
            var acknowledgement = Encoding.UTF8.GetBytes(_serializer.Serialize(
                new Dictionary<string, object> { { "ack", requestId } }));
            await pipe.WriteAsync(acknowledgement, 0, acknowledgement.Length, cancellationToken).ConfigureAwait(false);
            ValidateEnvelope(responseBytes, requestId, correlationId);
            return responseBytes;
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

        private ManagementStatus ParseStatus(byte[] bytes)
        {
            var envelope = DeserializeEnvelope(bytes);
            if (!String.Equals(Text(envelope, "result"), "ok", StringComparison.Ordinal))
                throw new ManagementIpcException(Text(envelope, "code") ?? "INTERNAL_ERROR");
            var data = envelope["data"] as Dictionary<string, object>;
            if (data == null) throw new ManagementIpcException("INVALID_RESPONSE");
            var observed = ParseTimestamp(Text(data, "observed_at_utc") ?? Text(envelope, "observed_at_utc"));
            if (!observed.HasValue) throw new ManagementIpcException("INVALID_RESPONSE");
            var age = DateTime.UtcNow - observed.Value;
            var stale = age > TimeSpan.FromSeconds(15) || age < TimeSpan.FromMinutes(-2);
            var source = Text(data, "source_identity") ?? "UNKNOWN";
            if (source.Length > 96)
                throw new ManagementIpcException("INVALID_RESPONSE");
            var mt5State = Text(data, "mt5_state");
            var legacyMt5Connected = BoolValue(data, "mt5_connected");
            if (String.IsNullOrWhiteSpace(mt5State))
                mt5State = data.ContainsKey("mt5_connected") ? (legacyMt5Connected ? "CONNECTED" : "DISCONNECTED") : "UNKNOWN";
            return new ManagementStatus
            {
                ServiceState = Text(data, "service_state") ?? "UNKNOWN",
                AgentState = Text(data, "agent_state") ?? "UNKNOWN",
                AgentLifecycleState = Text(data, "agent_lifecycle_state") ?? "UNKNOWN",
                AgentVersion = Text(data, "agent_version") ?? "UNKNOWN",
                ManagementProtocolVersion = IntValue(data, "management_protocol_version"),
                ManagementState = "CONNECTED",
                WorkerState = Text(data, "worker_state") ?? "UNKNOWN",
                RuntimeState = Text(data, "runtime_state") ?? "UNKNOWN",
                Mt5State = mt5State,
                Mt5Connected = String.Equals(mt5State, "CONNECTED", StringComparison.Ordinal),
                WorkerSessionId = NullableIntValue(data, "worker_session_id"),
                WorkerProtocolVersion = Text(data, "worker_protocol_version"),
                LastSuccessfulMt5Operation = Text(data, "last_successful_mt5_operation"),
                CentralState = Text(data, "central_state") ?? "NOT_CONFIGURED",
                TradingCapability = Text(data, "trading_capability") ?? "UNSUPPORTED",
                TradingAuthorized = Text(data, "trading_authorized") ?? "UNKNOWN",
                TradingReadiness = Text(data, "trading_readiness") ?? "UNAVAILABLE",
                SourceIdentity = source,
                CorrelationId = Text(envelope, "correlation_id"),
                Freshness = stale ? "STALE" : (Text(data, "freshness") ?? "FRESH"),
                IsObserved = true, IsStale = stale || String.Equals(Text(data, "freshness"), "STALE", StringComparison.Ordinal),
                ObservedAtUtc = observed, ErrorCode = Text(data, "error_code") ?? "OK", Reason = Text(envelope, "message")
            };
        }

        private Dictionary<string, object> DeserializeEnvelope(byte[] bytes)
        {
            try
            {
                var envelope = _serializer.Deserialize<Dictionary<string, object>>(Encoding.UTF8.GetString(bytes));
                if (envelope == null || IntValue(envelope, "protocol_version") != ProtocolVersion)
                    throw new ManagementIpcException("PROTOCOL_MISMATCH");
                return envelope;
            }
            catch (ManagementIpcException) { throw; }
            catch (Exception ex) { throw new ManagementIpcException("INVALID_RESPONSE", ex); }
        }

        private void ValidateEnvelope(byte[] bytes, string requestId, string correlationId)
        {
            var envelope = DeserializeEnvelope(bytes);
            if (!String.Equals(Text(envelope, "request_id"), requestId, StringComparison.Ordinal) ||
                !String.Equals(Text(envelope, "correlation_id"), correlationId, StringComparison.Ordinal))
                throw new ManagementIpcException("CORRELATION_MISMATCH");
            if (String.Equals(Text(envelope, "result"), "error", StringComparison.Ordinal))
                throw new ManagementIpcException(Text(envelope, "code") ?? "INTERNAL_ERROR");
        }

        private static string Text(IDictionary<string, object> data, string key)
        { object value; return data.TryGetValue(key, out value) ? value as string : null; }

        private static string ReadText(object value, string key)
        {
            var generic = value as IDictionary<string, object>;
            if (generic != null) return Text(generic, key);
            var dictionary = value as System.Collections.IDictionary;
            return dictionary == null ? null : dictionary[key] as string;
        }

        private static int IntValue(IDictionary<string, object> data, string key)
        { object value; return data.TryGetValue(key, out value) ? Convert.ToInt32(value, CultureInfo.InvariantCulture) : -1; }

        private static int? NullableIntValue(IDictionary<string, object> data, string key)
        {
            object value;
            if (!data.TryGetValue(key, out value) || value == null) return null;
            try { return Convert.ToInt32(value, CultureInfo.InvariantCulture); }
            catch (Exception) { throw new ManagementIpcException("INVALID_RESPONSE"); }
        }

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
