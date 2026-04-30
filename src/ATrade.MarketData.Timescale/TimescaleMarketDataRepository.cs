using System.Text.Json;
using ATrade.MarketData;
using Npgsql;
using NpgsqlTypes;

namespace ATrade.MarketData.Timescale;

public interface ITimescaleMarketDataRepository
{
    Task UpsertCandleSeriesAsync(TimescaleCandleSeries series, CancellationToken cancellationToken = default);

    Task<TimescaleCandleSeries?> GetFreshCandleSeriesAsync(TimescaleFreshCandleSeriesQuery query, CancellationToken cancellationToken = default);

    Task UpsertTrendingSnapshotAsync(TimescaleTrendingSnapshot snapshot, CancellationToken cancellationToken = default);

    Task<TimescaleTrendingSnapshot?> GetFreshTrendingSnapshotAsync(TimescaleFreshTrendingSnapshotQuery query, CancellationToken cancellationToken = default);
}

public sealed class TimescaleMarketDataRepository(ITimescaleMarketDataDataSourceProvider dataSourceProvider, TimeProvider timeProvider) : ITimescaleMarketDataRepository
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public TimescaleMarketDataRepository(ITimescaleMarketDataDataSourceProvider dataSourceProvider)
        : this(dataSourceProvider, TimeProvider.System)
    {
    }

    public async Task UpsertCandleSeriesAsync(TimescaleCandleSeries series, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(series);
        ArgumentNullException.ThrowIfNull(series.Symbol);

        if (series.Candles.Count == 0)
        {
            return;
        }

        try
        {
            await using var connection = await dataSourceProvider.GetDataSource().OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
            await using var transaction = await connection.BeginTransactionAsync(cancellationToken).ConfigureAwait(false);
            var writtenAtUtc = timeProvider.GetUtcNow();
            foreach (var candle in series.Candles)
            {
                await using var command = connection.CreateCommand();
                command.Transaction = transaction;
                command.CommandText = TimescaleMarketDataSql.UpsertCandle;
                AddSymbolParameters(command, series.Symbol);
                command.Parameters.AddWithValue("source", NpgsqlDbType.Text, NormalizeRequired(series.Source, nameof(series.Source)));
                command.Parameters.AddWithValue("timeframe", NpgsqlDbType.Text, NormalizeRequired(series.Timeframe, nameof(series.Timeframe)));
                command.Parameters.AddWithValue("candle_time_utc", NpgsqlDbType.TimestampTz, ToUtc(candle.Time));
                command.Parameters.AddWithValue("generated_at_utc", NpgsqlDbType.TimestampTz, ToUtc(series.GeneratedAtUtc));
                command.Parameters.AddWithValue("open", NpgsqlDbType.Numeric, candle.Open);
                command.Parameters.AddWithValue("high", NpgsqlDbType.Numeric, candle.High);
                command.Parameters.AddWithValue("low", NpgsqlDbType.Numeric, candle.Low);
                command.Parameters.AddWithValue("close", NpgsqlDbType.Numeric, candle.Close);
                command.Parameters.AddWithValue("volume", NpgsqlDbType.Bigint, candle.Volume);
                command.Parameters.AddWithValue("written_at_utc", NpgsqlDbType.TimestampTz, ToUtc(writtenAtUtc));
                await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            }

            await transaction.CommitAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (TimescaleMarketDataStorageUnavailableException)
        {
            throw;
        }
        catch (NpgsqlException exception)
        {
            throw new TimescaleMarketDataStorageUnavailableException("Timescale market-data candle upsert failed.", exception);
        }
    }

    public async Task<TimescaleCandleSeries?> GetFreshCandleSeriesAsync(TimescaleFreshCandleSeriesQuery query, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(query);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(TimescaleMarketDataSql.SelectFreshCandles);
            command.Parameters.AddWithValue("provider", NpgsqlDbType.Text, NormalizeRequired(query.Provider, nameof(query.Provider)));
            command.Parameters.AddWithValue("source", NpgsqlDbType.Text, NormalizeRequired(query.Source, nameof(query.Source)));
            command.Parameters.AddWithValue("symbol", NpgsqlDbType.Text, NormalizeRequired(query.Symbol, nameof(query.Symbol)));
            command.Parameters.AddWithValue("timeframe", NpgsqlDbType.Text, NormalizeRequired(query.Timeframe, nameof(query.Timeframe)));
            command.Parameters.AddWithValue("freshness_cutoff_utc", NpgsqlDbType.TimestampTz, ToUtc(query.FreshnessCutoffUtc));

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            TimescaleMarketDataSymbol? symbol = null;
            string? source = null;
            string? timeframe = null;
            DateTimeOffset generatedAtUtc = default;
            var candles = new List<OhlcvCandle>();

            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                symbol ??= ReadSymbol(reader, offset: 0);
                source ??= reader.GetString(1);
                timeframe ??= reader.GetString(8);
                var rowGeneratedAtUtc = reader.GetFieldValue<DateTimeOffset>(10);
                if (rowGeneratedAtUtc > generatedAtUtc)
                {
                    generatedAtUtc = rowGeneratedAtUtc;
                }

                candles.Add(new OhlcvCandle(
                    reader.GetFieldValue<DateTimeOffset>(9),
                    reader.GetDecimal(11),
                    reader.GetDecimal(12),
                    reader.GetDecimal(13),
                    reader.GetDecimal(14),
                    reader.GetInt64(15)));
            }

            return symbol is null || source is null || timeframe is null || candles.Count == 0
                ? null
                : new TimescaleCandleSeries(symbol, timeframe, source, generatedAtUtc, candles);
        }
        catch (TimescaleMarketDataStorageUnavailableException)
        {
            throw;
        }
        catch (NpgsqlException exception)
        {
            throw new TimescaleMarketDataStorageUnavailableException("Timescale market-data candle read failed.", exception);
        }
    }

    public async Task UpsertTrendingSnapshotAsync(TimescaleTrendingSnapshot snapshot, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(snapshot);

        if (snapshot.Symbols.Count == 0)
        {
            return;
        }

        try
        {
            await using var connection = await dataSourceProvider.GetDataSource().OpenConnectionAsync(cancellationToken).ConfigureAwait(false);
            await using var transaction = await connection.BeginTransactionAsync(cancellationToken).ConfigureAwait(false);
            var writtenAtUtc = timeProvider.GetUtcNow();
            foreach (var trendingSymbol in snapshot.Symbols)
            {
                ArgumentNullException.ThrowIfNull(trendingSymbol.Symbol);

                await using var command = connection.CreateCommand();
                command.Transaction = transaction;
                command.CommandText = TimescaleMarketDataSql.UpsertTrendingSnapshotSymbol;
                AddSymbolParameters(command, trendingSymbol.Symbol, snapshot.Provider);
                command.Parameters.AddWithValue("source", NpgsqlDbType.Text, NormalizeRequired(snapshot.Source, nameof(snapshot.Source)));
                command.Parameters.AddWithValue("sector", NpgsqlDbType.Text, NullableValue(trendingSymbol.Sector));
                command.Parameters.AddWithValue("generated_at_utc", NpgsqlDbType.TimestampTz, ToUtc(snapshot.GeneratedAtUtc));
                command.Parameters.AddWithValue("last_price", NpgsqlDbType.Numeric, trendingSymbol.LastPrice);
                command.Parameters.AddWithValue("change_percent", NpgsqlDbType.Numeric, trendingSymbol.ChangePercent);
                command.Parameters.AddWithValue("score", NpgsqlDbType.Numeric, trendingSymbol.Score);
                command.Parameters.AddWithValue("volume_spike", NpgsqlDbType.Numeric, trendingSymbol.Factors.VolumeSpike);
                command.Parameters.AddWithValue("price_momentum", NpgsqlDbType.Numeric, trendingSymbol.Factors.PriceMomentum);
                command.Parameters.AddWithValue("volatility", NpgsqlDbType.Numeric, trendingSymbol.Factors.Volatility);
                command.Parameters.AddWithValue("external_signal", NpgsqlDbType.Numeric, trendingSymbol.Factors.ExternalSignal);
                command.Parameters.AddWithValue("reasons", NpgsqlDbType.Jsonb, JsonSerializer.Serialize(trendingSymbol.Reasons, JsonOptions));
                command.Parameters.AddWithValue("written_at_utc", NpgsqlDbType.TimestampTz, ToUtc(writtenAtUtc));
                await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            }

            await transaction.CommitAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (TimescaleMarketDataStorageUnavailableException)
        {
            throw;
        }
        catch (NpgsqlException exception)
        {
            throw new TimescaleMarketDataStorageUnavailableException("Timescale market-data trending snapshot upsert failed.", exception);
        }
    }

    public async Task<TimescaleTrendingSnapshot?> GetFreshTrendingSnapshotAsync(TimescaleFreshTrendingSnapshotQuery query, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(query);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(TimescaleMarketDataSql.SelectFreshTrendingSnapshot);
            command.Parameters.AddWithValue("provider", NpgsqlDbType.Text, NormalizeRequired(query.Provider, nameof(query.Provider)));
            command.Parameters.AddWithValue("source", NpgsqlDbType.Text, NormalizeRequired(query.Source, nameof(query.Source)));
            command.Parameters.AddWithValue("freshness_cutoff_utc", NpgsqlDbType.TimestampTz, ToUtc(query.FreshnessCutoffUtc));
            command.Parameters.AddWithValue("symbol", NpgsqlDbType.Text, NullableValue(NormalizeOptional(query.Symbol)));

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            string? provider = null;
            string? source = null;
            DateTimeOffset generatedAtUtc = default;
            var symbols = new List<TimescaleTrendingSnapshotSymbol>();

            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                provider ??= reader.GetString(0);
                source ??= reader.GetString(1);
                generatedAtUtc = reader.GetFieldValue<DateTimeOffset>(9);
                symbols.Add(ReadTrendingSnapshotSymbol(reader));
            }

            return provider is null || source is null || symbols.Count == 0
                ? null
                : new TimescaleTrendingSnapshot(provider, source, generatedAtUtc, symbols);
        }
        catch (TimescaleMarketDataStorageUnavailableException)
        {
            throw;
        }
        catch (NpgsqlException exception)
        {
            throw new TimescaleMarketDataStorageUnavailableException("Timescale market-data trending snapshot read failed.", exception);
        }
    }

    private static void AddSymbolParameters(NpgsqlCommand command, TimescaleMarketDataSymbol symbol, string? providerOverride = null)
    {
        command.Parameters.AddWithValue("provider", NpgsqlDbType.Text, NormalizeRequired(providerOverride ?? symbol.Provider, nameof(symbol.Provider)));
        command.Parameters.AddWithValue("provider_symbol_id", NpgsqlDbType.Text, NullableValue(NormalizeOptional(symbol.ProviderSymbolId)));
        command.Parameters.AddWithValue("symbol", NpgsqlDbType.Text, NormalizeRequired(symbol.Symbol, nameof(symbol.Symbol)));
        command.Parameters.AddWithValue("name", NpgsqlDbType.Text, NullableValue(NormalizeOptional(symbol.Name)));
        command.Parameters.AddWithValue("exchange", NpgsqlDbType.Text, NullableValue(NormalizeOptional(symbol.Exchange)));
        command.Parameters.AddWithValue("currency", NpgsqlDbType.Text, NullableValue(NormalizeOptional(symbol.Currency)));
        command.Parameters.AddWithValue("asset_class", NpgsqlDbType.Text, NullableValue(NormalizeOptional(symbol.AssetClass)));
    }

    private static TimescaleMarketDataSymbol ReadSymbol(NpgsqlDataReader reader, int offset) => new(
        reader.GetString(offset),
        reader.IsDBNull(offset + 2) ? null : reader.GetString(offset + 2),
        reader.GetString(offset + 3),
        reader.IsDBNull(offset + 4) ? null : reader.GetString(offset + 4),
        reader.IsDBNull(offset + 5) ? null : reader.GetString(offset + 5),
        reader.IsDBNull(offset + 6) ? null : reader.GetString(offset + 6),
        reader.IsDBNull(offset + 7) ? null : reader.GetString(offset + 7));

    private static TimescaleTrendingSnapshotSymbol ReadTrendingSnapshotSymbol(NpgsqlDataReader reader) => new(
        ReadSymbol(reader, offset: 0),
        reader.IsDBNull(8) ? null : reader.GetString(8),
        reader.GetDecimal(10),
        reader.GetDecimal(11),
        reader.GetDecimal(12),
        new TrendingFactorBreakdown(
            reader.GetDecimal(13),
            reader.GetDecimal(14),
            reader.GetDecimal(15),
            reader.GetDecimal(16)),
        ReadReasons(reader));

    private static IReadOnlyList<string> ReadReasons(NpgsqlDataReader reader)
    {
        if (reader.IsDBNull(17))
        {
            return Array.Empty<string>();
        }

        return JsonSerializer.Deserialize<string[]>(reader.GetString(17), JsonOptions) ?? Array.Empty<string>();
    }

    private static string NormalizeRequired(string value, string parameterName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(value, parameterName);
        return value.Trim();
    }

    private static string? NormalizeOptional(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    private static DateTimeOffset ToUtc(DateTimeOffset value) => value.ToUniversalTime();

    private static object NullableValue(string? value) => value is null ? DBNull.Value : value;
}
