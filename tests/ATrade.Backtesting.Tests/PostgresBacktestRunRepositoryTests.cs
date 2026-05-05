using System.Text.Json;
using ATrade.Backtesting;
using ATrade.MarketData;

namespace ATrade.Backtesting.Tests;

public sealed class PostgresBacktestRunRepositoryTests
{
    [Fact]
    public void Initialize_IsIdempotentScopedAndNamespacedWithoutSensitiveColumns()
    {
        var sql = PostgresBacktestRunSql.Initialize;

        Assert.Contains("CREATE SCHEMA IF NOT EXISTS atrade_backtesting", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE TABLE IF NOT EXISTS atrade_backtesting.saved_backtest_runs", sql, StringComparison.Ordinal);
        Assert.Contains("user_id text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("workspace_id text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("run_id text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("source_run_id text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("status text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("request_json jsonb NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("result_json jsonb NULL", sql, StringComparison.Ordinal);
        Assert.Contains("PRIMARY KEY (user_id, workspace_id, run_id)", sql, StringComparison.Ordinal);
        Assert.Contains("CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'))", sql, StringComparison.Ordinal);
        Assert.Contains("ADD COLUMN IF NOT EXISTS request_json", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX IF NOT EXISTS ix_saved_backtest_runs_workspace_created", sql, StringComparison.Ordinal);

        AssertNoSensitivePersistenceTerms(sql);
    }

    [Fact]
    public void RepositoryStatements_AreWorkspaceScopedAndSupportStatusCancelAndRetryFromSavedSnapshot()
    {
        Assert.Contains("WHERE user_id = @user_id", PostgresBacktestRunSql.SelectByWorkspace, StringComparison.Ordinal);
        Assert.Contains("AND workspace_id = @workspace_id", PostgresBacktestRunSql.SelectByWorkspace, StringComparison.Ordinal);
        Assert.Contains("ORDER BY created_at_utc DESC, run_id DESC", PostgresBacktestRunSql.SelectByWorkspace, StringComparison.Ordinal);
        Assert.Contains("LIMIT @limit", PostgresBacktestRunSql.SelectByWorkspace, StringComparison.Ordinal);

        Assert.Contains("WHERE user_id = @user_id", PostgresBacktestRunSql.SelectByRunId, StringComparison.Ordinal);
        Assert.Contains("AND workspace_id = @workspace_id", PostgresBacktestRunSql.SelectByRunId, StringComparison.Ordinal);
        Assert.Contains("AND run_id = @run_id", PostgresBacktestRunSql.SelectByRunId, StringComparison.Ordinal);

        Assert.Contains("SET status = @status", PostgresBacktestRunSql.UpdateStatus, StringComparison.Ordinal);
        Assert.Contains("error_code = @error_code", PostgresBacktestRunSql.UpdateStatus, StringComparison.Ordinal);
        Assert.Contains("result_json = COALESCE(@result_json, result_json)", PostgresBacktestRunSql.UpdateStatus, StringComparison.Ordinal);
        Assert.Contains("WHEN @status IN ('completed', 'failed', 'cancelled')", PostgresBacktestRunSql.UpdateStatus, StringComparison.Ordinal);

        Assert.Contains("SET status = 'cancelled'", PostgresBacktestRunSql.CancelRun, StringComparison.Ordinal);
        Assert.Contains("AND status IN ('queued', 'running')", PostgresBacktestRunSql.CancelRun, StringComparison.Ordinal);

        Assert.Contains("WITH retry_source AS", PostgresBacktestRunSql.InsertRetryRun, StringComparison.Ordinal);
        Assert.Contains("AND status IN ('failed', 'cancelled')", PostgresBacktestRunSql.InsertRetryRun, StringComparison.Ordinal);
        Assert.Contains("SELECT request_json", PostgresBacktestRunSql.InsertRetryRun, StringComparison.Ordinal);
        Assert.DoesNotContain("@request_json", PostgresBacktestRunSql.InsertRetryRun, StringComparison.Ordinal);

        AssertNoSensitivePersistenceTerms(PostgresBacktestRunSql.InsertRun);
        AssertNoSensitivePersistenceTerms(PostgresBacktestRunSql.UpdateStatus);
        AssertNoSensitivePersistenceTerms(PostgresBacktestRunSql.CancelRun);
        AssertNoSensitivePersistenceTerms(PostgresBacktestRunSql.InsertRetryRun);
    }

    [Fact]
    public void PersistenceSafety_SerializesOnlyCanonicalSafeRequestSnapshot()
    {
        var json = BacktestPersistenceSafety.SerializeRequestSnapshot(SafeSnapshot());

        Assert.Contains("\"strategyId\":\"sma-crossover\"", json, StringComparison.Ordinal);
        Assert.Contains("\"chartRange\":\"1y\"", json, StringComparison.Ordinal);
        Assert.Contains("\"parameters\"", json, StringComparison.Ordinal);
        Assert.DoesNotContain("symbolCode", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("bars", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("account", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("gateway", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("cookie", json, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void PersistenceSafety_RejectsDirectBarsSecretsAccountIdentifiersAndGatewayUrls()
    {
        AssertRejected(SafeSnapshot() with
        {
            Parameters = new Dictionary<string, JsonElement>
            {
                ["candles"] = Json("[]"),
            },
        });
        AssertRejected(SafeSnapshot() with
        {
            Parameters = new Dictionary<string, JsonElement>
            {
                ["token"] = Json("\"abc123\""),
            },
        });
        AssertRejected(SafeSnapshot() with
        {
            Parameters = new Dictionary<string, JsonElement>
            {
                ["riskBucket"] = Json("\"DU1234567\""),
            },
        });
        AssertRejected(SafeSnapshot() with
        {
            Parameters = new Dictionary<string, JsonElement>
            {
                ["endpoint"] = Json("\"https://127.0.0.1:5000/v1/api\""),
            },
        });
    }

    [Fact]
    public void PersistenceSafety_RedactsSensitiveErrorMessagesBeforeStorage()
    {
        var safeError = BacktestPersistenceSafety.NormalizeSafeError(new BacktestError(
            BacktestErrorCodes.StorageUnavailable,
            "gateway https://127.0.0.1:5000 leaked account DU1234567 token abc"));

        Assert.NotNull(safeError);
        Assert.Equal(BacktestErrorCodes.StorageUnavailable, safeError.Code);
        Assert.Contains("redacted", safeError.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("https://", safeError.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("DU1234567", safeError.Message, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", safeError.Message, StringComparison.OrdinalIgnoreCase);
    }

    private static BacktestRequestSnapshot SafeSnapshot() => BacktestRequestValidator.Validate(new BacktestCreateRequest(
        Symbol: MarketDataSymbolIdentity.Create("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
        SymbolCode: null,
        StrategyId: BacktestStrategyIds.SmaCrossover,
        Parameters: new Dictionary<string, JsonElement>
        {
            ["fastPeriod"] = Json("20"),
            ["slowPeriod"] = Json("50"),
        },
        ChartRange: ChartRangePresets.OneYear,
        CostModel: new BacktestCostModel(0m, 0m, "USD"),
        SlippageBps: 0m,
        BenchmarkMode: BacktestBenchmarkModes.None));

    private static void AssertRejected(BacktestRequestSnapshot snapshot)
    {
        var exception = Assert.Throws<BacktestValidationException>(() => BacktestPersistenceSafety.SerializeRequestSnapshot(snapshot));
        Assert.True(
            exception.Code is BacktestErrorCodes.ForbiddenField or BacktestErrorCodes.UnsupportedScope,
            $"Unexpected rejection code: {exception.Code}");
    }

    private static JsonElement Json(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

    private static void AssertNoSensitivePersistenceTerms(string sql)
    {
        Assert.DoesNotContain("account_id", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("accountId", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("credential", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("password", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("secret", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("cookie", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("session", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("gateway", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("url", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("candles", sql, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("bars", sql, StringComparison.OrdinalIgnoreCase);
    }
}
