namespace ATrade.MarketData;

public sealed class MockMarketDataService(IndicatorService indicatorService, TrendingService trendingService) : IMarketDataService
{
    private static readonly DateTimeOffset AnchorTime = new(2026, 4, 29, 20, 0, 0, TimeSpan.Zero);

    private static readonly IReadOnlyList<MarketDataSymbol> SymbolCatalog = new[]
    {
        new MarketDataSymbol("AAPL", "Apple Inc.", "Stock", "NASDAQ", "Technology", 196.44m, 1.18m, 58_000_000),
        new MarketDataSymbol("MSFT", "Microsoft Corporation", "Stock", "NASDAQ", "Technology", 437.92m, 0.74m, 23_000_000),
        new MarketDataSymbol("NVDA", "NVIDIA Corporation", "Stock", "NASDAQ", "Semiconductors", 123.41m, 2.86m, 241_000_000),
        new MarketDataSymbol("SPY", "SPDR S&P 500 ETF Trust", "ETF", "NYSEARCA", "Broad Market", 512.18m, 0.42m, 71_000_000),
        new MarketDataSymbol("QQQ", "Invesco QQQ Trust", "ETF", "NASDAQ", "Growth ETF", 438.67m, 0.63m, 48_000_000),
        new MarketDataSymbol("IWM", "iShares Russell 2000 ETF", "ETF", "NYSEARCA", "Small Cap ETF", 202.31m, -0.21m, 31_000_000),
    };

    public TrendingSymbolsResponse GetTrendingSymbols()
    {
        var symbols = SymbolCatalog
            .Select(symbol => trendingService.CreateTrendingSymbol(symbol, GenerateCandles(symbol, MarketDataTimeframes.OneDay)))
            .OrderByDescending(symbol => symbol.Score)
            .ToArray();

        return new TrendingSymbolsResponse(AnchorTime, symbols);
    }

    public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol)
    {
        marketSymbol = SymbolCatalog.FirstOrDefault(candidate => string.Equals(candidate.Symbol, symbol, StringComparison.OrdinalIgnoreCase));
        return marketSymbol is not null;
    }

    public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryValidate(symbol, timeframe, out var marketSymbol, out var definition, out error))
        {
            return false;
        }

        response = new CandleSeriesResponse(
            marketSymbol.Symbol,
            definition.Name,
            AnchorTime,
            GenerateCandles(marketSymbol, definition.Name));
        return true;
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryValidate(symbol, timeframe, out var marketSymbol, out var definition, out error))
        {
            return false;
        }

        response = indicatorService.Calculate(
            marketSymbol.Symbol,
            definition.Name,
            GenerateCandles(marketSymbol, definition.Name));
        return true;
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
    {
        update = null;
        if (!TryValidate(symbol, timeframe, out var marketSymbol, out var definition, out error))
        {
            return false;
        }

        var candles = GenerateCandles(marketSymbol, definition.Name);
        var latest = candles[^1];
        var previous = candles[^2];
        update = new MarketDataUpdate(
            marketSymbol.Symbol,
            definition.Name,
            latest.Time,
            latest.Open,
            latest.High,
            latest.Low,
            latest.Close,
            latest.Volume,
            Round((latest.Close - previous.Close) / previous.Close * 100m),
            "mock-deterministic");
        return true;
    }

    private static bool TryValidate(
        string symbol,
        string? timeframe,
        out MarketDataSymbol marketSymbol,
        out TimeframeDefinition definition,
        out MarketDataError? error)
    {
        marketSymbol = null!;
        definition = default;
        error = null;

        if (string.IsNullOrWhiteSpace(symbol) || !TryFindSymbol(symbol, out var foundSymbol))
        {
            error = new MarketDataError("unsupported-symbol", $"Symbol '{symbol}' is not available in the mocked market-data catalog.");
            return false;
        }

        if (!MarketDataTimeframes.TryGetDefinition(timeframe, out definition))
        {
            error = new MarketDataError(
                "unsupported-timeframe",
                $"Timeframe '{timeframe}' is not supported. Supported values: {string.Join(", ", MarketDataTimeframes.Supported)}.");
            return false;
        }

        marketSymbol = foundSymbol;
        return true;
    }

    private static bool TryFindSymbol(string symbol, out MarketDataSymbol marketSymbol)
    {
        var result = SymbolCatalog.FirstOrDefault(candidate => string.Equals(candidate.Symbol, symbol, StringComparison.OrdinalIgnoreCase));
        marketSymbol = result!;
        return result is not null;
    }

    private static IReadOnlyList<OhlcvCandle> GenerateCandles(MarketDataSymbol symbol, string timeframe)
    {
        if (!MarketDataTimeframes.TryGetDefinition(timeframe, out var definition))
        {
            throw new ArgumentOutOfRangeException(nameof(timeframe), timeframe, "Unsupported mocked market-data timeframe.");
        }

        var seed = StableHash(symbol.Symbol + definition.Name);
        var candles = new List<OhlcvCandle>(definition.CandleCount);
        var previousClose = symbol.LastPrice * (1m - (symbol.ChangePercent / 100m));
        var trendDirection = seed % 2 == 0 ? 1m : -1m;
        var trendStep = symbol.LastPrice * 0.00018m * trendDirection;

        for (var index = 0; index < definition.CandleCount; index++)
        {
            var time = AnchorTime - (definition.Step * (definition.CandleCount - index - 1));
            var wave = (decimal)Math.Sin((index + (seed % 23)) / 6.0) * symbol.LastPrice * 0.005m;
            var microWave = (decimal)Math.Cos((index + (seed % 11)) / 3.0) * symbol.LastPrice * 0.0015m;
            var close = Round(Math.Max(1m, symbol.LastPrice + (trendStep * (index - (definition.CandleCount / 2m))) + wave + microWave));
            var open = Round(previousClose);
            var range = Round(symbol.LastPrice * (0.002m + ((seed + index) % 9) * 0.00035m));
            var high = Round(Math.Max(open, close) + range);
            var low = Round(Math.Max(0.01m, Math.Min(open, close) - range));
            var volumeMultiplier = 0.78m + (((seed + (index * 13)) % 55) / 100m);
            var volume = (long)(symbol.AverageVolume * volumeMultiplier / Math.Max(1, definition.CandleCount / 20));

            candles.Add(new OhlcvCandle(time, open, high, low, close, Math.Max(1, volume)));
            previousClose = close;
        }

        return candles;
    }

    private static int StableHash(string value)
    {
        var hash = 17;
        foreach (var character in value.ToUpperInvariant())
        {
            hash = unchecked((hash * 31) + character);
        }

        return Math.Abs(hash % 10_000);
    }

    private static decimal Round(decimal value) => Math.Round(value, 4, MidpointRounding.AwayFromZero);
}
