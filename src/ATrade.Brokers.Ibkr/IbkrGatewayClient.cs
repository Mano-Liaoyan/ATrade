using System.Net.Http.Json;
using System.Text.Json.Serialization;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrGatewayClient(HttpClient httpClient, IIbkrPaperTradingGuard paperTradingGuard) : IIbkrGatewayClient
{
    private const string AuthStatusPath = "/v1/api/iserver/auth/status";

    public async Task<IbkrGatewaySessionStatus> GetSessionStatusAsync(CancellationToken cancellationToken = default)
    {
        paperTradingGuard.EnsurePaperOnly();

        using var response = await httpClient.GetAsync(AuthStatusPath, cancellationToken).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();

        var payload = await response.Content.ReadFromJsonAsync<IbkrGatewayAuthStatusPayload>(cancellationToken: cancellationToken).ConfigureAwait(false)
            ?? throw new InvalidOperationException("IBKR Gateway returned an empty auth status payload.");

        return new IbkrGatewaySessionStatus(
            Authenticated: payload.Authenticated,
            Connected: payload.Connected,
            Competing: payload.Competing,
            Message: payload.Message,
            ServerName: payload.ServerInfo?.ServerName,
            ServerVersion: payload.ServerInfo?.ServerVersion);
    }

    private sealed class IbkrGatewayAuthStatusPayload
    {
        [JsonPropertyName("authenticated")]
        public bool Authenticated { get; init; }

        [JsonPropertyName("connected")]
        public bool Connected { get; init; }

        [JsonPropertyName("competing")]
        public bool Competing { get; init; }

        [JsonPropertyName("message")]
        public string? Message { get; init; }

        [JsonPropertyName("serverInfo")]
        public IbkrGatewayServerInfoPayload? ServerInfo { get; init; }
    }

    private sealed class IbkrGatewayServerInfoPayload
    {
        [JsonPropertyName("serverName")]
        public string? ServerName { get; init; }

        [JsonPropertyName("serverVersion")]
        public string? ServerVersion { get; init; }
    }
}
