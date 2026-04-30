using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using ATrade.Brokers.Ibkr;

namespace ATrade.MarketData.Ibkr;

public interface IIbkrMarketDataClient
{
    Task<IbkrGatewaySessionStatus> GetAuthStatusAsync(CancellationToken cancellationToken = default);

    Task<IReadOnlyList<IbkrContract>> SearchContractsAsync(string query, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<IbkrMarketDataSnapshot>> GetSnapshotsAsync(IReadOnlyList<string> conids, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<IbkrHistoricalBar>> GetHistoricalBarsAsync(string conid, string period, string bar, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<IbkrScannerResult>> GetTrendingScannerResultsAsync(CancellationToken cancellationToken = default);
}

public sealed class IbkrMarketDataClient(HttpClient httpClient) : IIbkrMarketDataClient
{
    public const string AuthStatusPath = "/v1/api/iserver/auth/status";
    public const string ContractSearchPath = "/v1/api/iserver/secdef/search";
    public const string ContractInfoPath = "/v1/api/iserver/secdef/info";
    public const string SnapshotPath = "/v1/api/iserver/marketdata/snapshot";
    public const string HistoricalDataPath = "/v1/api/iserver/marketdata/history";
    public const string ScannerPath = "/v1/api/iserver/scanner/run";

    private const string SnapshotFields = "31,55,70,71,82,83,84,86,87,7292,7295,7296,6509";

    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        NumberHandling = JsonNumberHandling.AllowReadingFromString,
    };

    public async Task<IbkrGatewaySessionStatus> GetAuthStatusAsync(CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.GetAsync(AuthStatusPath, cancellationToken).ConfigureAwait(false);
        await EnsureMarketDataSuccessAsync(response, cancellationToken).ConfigureAwait(false);

        var payload = await response.Content.ReadFromJsonAsync<IbkrGatewayAuthStatusPayload>(JsonOptions, cancellationToken).ConfigureAwait(false)
            ?? throw new IbkrMarketDataProviderException(MarketDataProviderErrorCodes.ProviderUnavailable, "IBKR iBeam returned an empty auth status payload.");

        return new IbkrGatewaySessionStatus(
            Authenticated: payload.Authenticated,
            Connected: payload.Connected,
            Competing: payload.Competing,
            Message: payload.Message,
            ServerName: payload.ServerInfo?.ServerName,
            ServerVersion: payload.ServerInfo?.ServerVersion);
    }

    public async Task<IReadOnlyList<IbkrContract>> SearchContractsAsync(string query, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(query);

        var path = $"{ContractSearchPath}?symbol={Uri.EscapeDataString(query.Trim())}&name=true&secType=STK";
        using var response = await httpClient.GetAsync(path, cancellationToken).ConfigureAwait(false);
        await EnsureMarketDataSuccessAsync(response, cancellationToken).ConfigureAwait(false);

        using var document = await ReadJsonDocumentAsync(response, cancellationToken).ConfigureAwait(false);
        var searchContracts = EnumerateResultItems(document.RootElement)
            .Select(element => ParseContract(element))
            .Where(contract => contract is not null)
            .Cast<IbkrContract>()
            .Take(MarketDataSymbolSearchLimits.MaximumLimit)
            .ToArray();

        var enrichedContracts = new List<IbkrContract>(searchContracts.Length);
        foreach (var contract in searchContracts)
        {
            enrichedContracts.Add(await GetContractInfoAsync(contract, cancellationToken).ConfigureAwait(false));
        }

        return enrichedContracts;
    }

    private async Task<IbkrContract> GetContractInfoAsync(IbkrContract contract, CancellationToken cancellationToken)
    {
        var path = $"{ContractInfoPath}?conid={Uri.EscapeDataString(contract.Conid)}&secType={Uri.EscapeDataString(ToIbkrSecType(contract.AssetClass))}";
        using var response = await httpClient.GetAsync(path, cancellationToken).ConfigureAwait(false);
        await EnsureMarketDataSuccessAsync(response, cancellationToken).ConfigureAwait(false);

        using var document = await ReadJsonDocumentAsync(response, cancellationToken).ConfigureAwait(false);
        var detail = EnumerateResultItems(document.RootElement)
            .Select(element => ParseContract(element, contract))
            .FirstOrDefault(parsed => parsed is not null);

        return detail is null ? contract : MergeContract(contract, detail);
    }

    public async Task<IReadOnlyList<IbkrMarketDataSnapshot>> GetSnapshotsAsync(IReadOnlyList<string> conids, CancellationToken cancellationToken = default)
    {
        if (conids.Count == 0)
        {
            return Array.Empty<IbkrMarketDataSnapshot>();
        }

        var conidCsv = string.Join(',', conids.Where(conid => !string.IsNullOrWhiteSpace(conid)).Select(conid => conid.Trim()).Distinct(StringComparer.OrdinalIgnoreCase));
        if (string.IsNullOrWhiteSpace(conidCsv))
        {
            return Array.Empty<IbkrMarketDataSnapshot>();
        }

        var path = $"{SnapshotPath}?conids={Uri.EscapeDataString(conidCsv)}&fields={Uri.EscapeDataString(SnapshotFields)}";
        using var response = await httpClient.GetAsync(path, cancellationToken).ConfigureAwait(false);
        await EnsureMarketDataSuccessAsync(response, cancellationToken).ConfigureAwait(false);

        using var document = await ReadJsonDocumentAsync(response, cancellationToken).ConfigureAwait(false);
        return EnumerateResultItems(document.RootElement)
            .Select(ParseSnapshot)
            .Where(snapshot => snapshot is not null)
            .Cast<IbkrMarketDataSnapshot>()
            .ToArray();
    }

    public async Task<IReadOnlyList<IbkrHistoricalBar>> GetHistoricalBarsAsync(string conid, string period, string bar, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(conid);
        ArgumentException.ThrowIfNullOrWhiteSpace(period);
        ArgumentException.ThrowIfNullOrWhiteSpace(bar);

        var path = $"{HistoricalDataPath}?conid={Uri.EscapeDataString(conid.Trim())}&period={Uri.EscapeDataString(period)}&bar={Uri.EscapeDataString(bar)}&outsideRth=true";
        using var response = await httpClient.GetAsync(path, cancellationToken).ConfigureAwait(false);
        await EnsureMarketDataSuccessAsync(response, cancellationToken).ConfigureAwait(false);

        using var document = await ReadJsonDocumentAsync(response, cancellationToken).ConfigureAwait(false);
        var items = document.RootElement.TryGetPropertyIgnoreCase("data", out var data)
            ? EnumerateResultItems(data)
            : EnumerateResultItems(document.RootElement);

        return items
            .Select(ParseHistoricalBar)
            .Where(candle => candle is not null)
            .Cast<IbkrHistoricalBar>()
            .OrderBy(candle => candle.Time)
            .ToArray();
    }

    public async Task<IReadOnlyList<IbkrScannerResult>> GetTrendingScannerResultsAsync(CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            ScannerPath,
            new
            {
                instrument = "STK",
                location = "STK.US.MAJOR",
                type = "TOP_PERC_GAIN",
                filter = Array.Empty<object>(),
            },
            JsonOptions,
            cancellationToken).ConfigureAwait(false);
        await EnsureMarketDataSuccessAsync(response, cancellationToken).ConfigureAwait(false);

        using var document = await ReadJsonDocumentAsync(response, cancellationToken).ConfigureAwait(false);
        return EnumerateResultItems(document.RootElement)
            .Select(ParseScannerResult)
            .Where(result => result is not null)
            .Cast<IbkrScannerResult>()
            .ToArray();
    }

    private static async Task<JsonDocument> ReadJsonDocumentAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        var json = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(json))
        {
            throw new IbkrMarketDataProviderException(MarketDataProviderErrorCodes.ProviderUnavailable, "IBKR iBeam returned an empty market-data payload.");
        }

        return JsonDocument.Parse(json);
    }

    private static async Task EnsureMarketDataSuccessAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        if (response.IsSuccessStatusCode)
        {
            return;
        }

        var body = response.Content is null
            ? string.Empty
            : await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        var redactedBody = body.Length > 512 ? body[..512] : body;

        if (response.StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden)
        {
            throw new IbkrMarketDataProviderException(
                MarketDataProviderErrorCodes.AuthenticationRequired,
                "IBKR iBeam rejected the market-data request because the session is not authenticated.");
        }

        throw new IbkrMarketDataProviderException(
            MarketDataProviderErrorCodes.ProviderUnavailable,
            $"IBKR iBeam market-data endpoint returned {(int)response.StatusCode} {response.ReasonPhrase}: {redactedBody}".Trim());
    }

    private static IEnumerable<JsonElement> EnumerateResultItems(JsonElement root)
    {
        if (root.ValueKind == JsonValueKind.Array)
        {
            return root.EnumerateArray().ToArray();
        }

        if (root.ValueKind != JsonValueKind.Object)
        {
            return Array.Empty<JsonElement>();
        }

        foreach (var name in new[] { "contracts", "results", "data", "items", "symbols" })
        {
            if (root.TryGetPropertyIgnoreCase(name, out var property) && property.ValueKind == JsonValueKind.Array)
            {
                return property.EnumerateArray().ToArray();
            }
        }

        return new[] { root };
    }

    private static IbkrContract? ParseContract(JsonElement element, IbkrContract? fallback = null)
    {
        var conid = element.GetStringValue("conid", "con_id", "contractId", "contract_id")
            ?? element.GetNestedStringValue("contract", "conid")
            ?? element.GetNestedStringValue("contract", "con_id")
            ?? fallback?.Conid;
        var symbol = element.GetStringValue("symbol", "ticker", "localSymbol")
            ?? element.GetNestedStringValue("contract", "symbol")
            ?? fallback?.Symbol;

        if (string.IsNullOrWhiteSpace(conid) || string.IsNullOrWhiteSpace(symbol))
        {
            return null;
        }

        var assetClass = element.GetStringValue("secType", "assetClass", "asset_class")
            ?? element.GetNestedStringValue("contract", "secType")
            ?? TryReadFirstSectionString(element, "secType", "assetClass")
            ?? fallback?.AssetClass
            ?? "Stock";
        var exchange = element.GetStringValue("exchange", "listingExchange", "listing_exchange", "primaryExchange")
            ?? element.GetNestedStringValue("contract", "exchange")
            ?? fallback?.Exchange
            ?? "SMART";
        var name = element.GetStringValue("companyName", "companyHeader", "description", "contract_description_1", "name")
            ?? fallback?.Name
            ?? symbol;
        var sector = element.GetStringValue("sector", "industry", "category") ?? fallback?.Sector ?? assetClass;
        var currency = element.GetStringValue("currency", "currencyCode", "baseCurrency")
            ?? element.GetNestedStringValue("contract", "currency")
            ?? TryReadFirstSectionString(element, "currency", "currencyCode")
            ?? fallback?.Currency
            ?? "USD";

        return new IbkrContract(NormalizeSymbol(symbol), name, NormalizeAssetClass(assetClass), exchange, conid, sector, NormalizeCurrency(currency));
    }

    private static IbkrContract MergeContract(IbkrContract searchContract, IbkrContract detailContract)
    {
        return new IbkrContract(
            string.IsNullOrWhiteSpace(detailContract.Symbol) ? searchContract.Symbol : detailContract.Symbol,
            string.IsNullOrWhiteSpace(detailContract.Name) ? searchContract.Name : detailContract.Name,
            string.IsNullOrWhiteSpace(detailContract.AssetClass) ? searchContract.AssetClass : detailContract.AssetClass,
            string.IsNullOrWhiteSpace(detailContract.Exchange) ? searchContract.Exchange : detailContract.Exchange,
            string.IsNullOrWhiteSpace(detailContract.Conid) ? searchContract.Conid : detailContract.Conid,
            string.IsNullOrWhiteSpace(detailContract.Sector) ? searchContract.Sector : detailContract.Sector,
            string.IsNullOrWhiteSpace(detailContract.Currency) ? searchContract.Currency : detailContract.Currency);
    }

    private static IbkrMarketDataSnapshot? ParseSnapshot(JsonElement element)
    {
        var conid = element.GetStringValue("conid", "con_id", "contractId", "_conid") ?? string.Empty;
        var symbol = element.GetStringValue("55", "symbol", "ticker", "localSymbol") ?? string.Empty;
        var lastPrice = element.GetDecimalValue("31", "lastPrice", "last", "price");
        var bid = element.GetDecimalValue("84", "bid");
        var ask = element.GetDecimalValue("86", "ask");
        if (lastPrice is null && bid is not null && ask is not null)
        {
            lastPrice = decimal.Round((bid.Value + ask.Value) / 2m, 4, MidpointRounding.AwayFromZero);
        }

        if (string.IsNullOrWhiteSpace(conid) && string.IsNullOrWhiteSpace(symbol) && lastPrice is null)
        {
            return null;
        }

        return new IbkrMarketDataSnapshot(
            conid,
            NormalizeSymbol(symbol),
            lastPrice,
            element.GetDecimalValue("83", "changePercent", "percentChange", "change_percent", "pctChange", "7289"),
            element.GetDecimalValue("7295", "open", "openPrice"),
            element.GetDecimalValue("70", "high", "highPrice"),
            element.GetDecimalValue("71", "low", "lowPrice"),
            element.GetInt64Value("87", "7296", "volume", "dayVolume"),
            DateTimeOffset.UtcNow);
    }

    private static IbkrHistoricalBar? ParseHistoricalBar(JsonElement element)
    {
        var timestamp = element.GetInt64Value("t", "time", "timestamp", "date");
        var open = element.GetDecimalValue("o", "open");
        var high = element.GetDecimalValue("h", "high");
        var low = element.GetDecimalValue("l", "low");
        var close = element.GetDecimalValue("c", "close");

        if (timestamp is null || open is null || high is null || low is null || close is null)
        {
            return null;
        }

        return new IbkrHistoricalBar(
            ToDateTimeOffset(timestamp.Value),
            Round(open.Value),
            Round(high.Value),
            Round(low.Value),
            Round(close.Value),
            element.GetInt64Value("v", "volume") ?? 0);
    }

    private static IbkrScannerResult? ParseScannerResult(JsonElement element)
    {
        var contractElement = element.TryGetPropertyIgnoreCase("contract", out var nestedContract) ? nestedContract : element;
        var contract = ParseContract(contractElement);
        if (contract is null)
        {
            var symbol = element.GetStringValue("symbol", "ticker", "localSymbol", "contract_description_1");
            var conid = element.GetStringValue("conid", "con_id", "contractId");
            if (string.IsNullOrWhiteSpace(symbol) || string.IsNullOrWhiteSpace(conid))
            {
                return null;
            }

            contract = new IbkrContract(
                NormalizeSymbol(symbol),
                element.GetStringValue("companyName", "description", "contract_description_2", "name") ?? symbol,
                NormalizeAssetClass(element.GetStringValue("secType", "assetClass", "asset_class") ?? "Stock"),
                element.GetStringValue("exchange", "listingExchange", "listing_exchange") ?? "SMART",
                conid,
                element.GetStringValue("sector", "industry", "category") ?? "Stock",
                NormalizeCurrency(element.GetStringValue("currency", "currencyCode", "baseCurrency") ?? "USD"));
        }

        return new IbkrScannerResult(
            contract.Symbol,
            contract.Name,
            contract.AssetClass,
            contract.Exchange,
            contract.Conid,
            contract.Sector,
            element.GetInt32Value("rank", "position", "sequence"),
            element.GetDecimalValue("score", "scanData", "scannerScore"),
            element.GetDecimalValue("lastPrice", "last", "price", "31"),
            element.GetDecimalValue("changePercent", "percentChange", "change_percent", "pctChange", "83"),
            element.GetInt64Value("volume", "dayVolume", "87", "7296"),
            IbkrMarketDataSource.Scanner);
    }

    private static string? TryReadFirstSectionString(JsonElement element, params string[] names)
    {
        if (!element.TryGetPropertyIgnoreCase("sections", out var sections) || sections.ValueKind != JsonValueKind.Array)
        {
            return null;
        }

        foreach (var section in sections.EnumerateArray())
        {
            var value = section.GetStringValue(names);
            if (!string.IsNullOrWhiteSpace(value))
            {
                return value;
            }
        }

        return null;
    }

    private static DateTimeOffset ToDateTimeOffset(long value)
    {
        return value > 100_000_000_000
            ? DateTimeOffset.FromUnixTimeMilliseconds(value)
            : DateTimeOffset.FromUnixTimeSeconds(value);
    }

    private static string NormalizeSymbol(string symbol) => symbol.Trim().ToUpperInvariant();

    private static string NormalizeCurrency(string currency) => currency.Trim().ToUpperInvariant();

    private static string ToIbkrSecType(string assetClass)
    {
        return assetClass.Trim().ToUpperInvariant() switch
        {
            "STOCK" or "STK" => "STK",
            "ETF" => "ETF",
            var normalized => normalized,
        };
    }

    private static string NormalizeAssetClass(string assetClass)
    {
        return assetClass.Trim().ToUpperInvariant() switch
        {
            "STK" => "Stock",
            "ETF" => "ETF",
            _ => assetClass.Trim(),
        };
    }

    private static decimal Round(decimal value) => decimal.Round(value, 4, MidpointRounding.AwayFromZero);

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
