using ATrade.Workspaces;

namespace ATrade.Workspaces.Tests;

public sealed class PostgresWorkspaceWatchlistSqlTests
{
    [Fact]
    public void Initialize_IsIdempotentAndIncludesFutureProviderMetadataColumns()
    {
        var sql = PostgresWorkspaceWatchlistSql.Initialize;

        Assert.Contains("CREATE SCHEMA IF NOT EXISTS atrade_workspaces", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE TABLE IF NOT EXISTS atrade_workspaces.workspace_watchlist_pins", sql, StringComparison.Ordinal);
        Assert.Contains("user_id text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("workspace_id text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("provider text NOT NULL DEFAULT 'manual'", sql, StringComparison.Ordinal);
        Assert.Contains("provider_symbol_id text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("ibkr_conid bigint NULL", sql, StringComparison.Ordinal);
        Assert.Contains("exchange text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("currency text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("asset_class text NULL", sql, StringComparison.Ordinal);
        Assert.Contains("sort_order integer NOT NULL DEFAULT 0", sql, StringComparison.Ordinal);
        Assert.Contains("PRIMARY KEY (user_id, workspace_id, symbol)", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX IF NOT EXISTS ix_workspace_watchlist_pins_workspace_order", sql, StringComparison.Ordinal);
    }

    [Fact]
    public void Upsert_DeduplicatesPinsByWorkspaceAndProviderIdentityWithoutReorderingExistingPins()
    {
        var sql = PostgresWorkspaceWatchlistSql.UpsertPinnedSymbol;

        Assert.Contains("deleted_provider_duplicate", sql, StringComparison.Ordinal);
        Assert.Contains("provider = @provider", sql, StringComparison.Ordinal);
        Assert.Contains("provider_symbol_id = @provider_symbol_id", sql, StringComparison.Ordinal);
        Assert.Contains("ibkr_conid = @ibkr_conid", sql, StringComparison.Ordinal);
        Assert.Contains("COALESCE(MAX(sort_order) + 1, 0)", sql, StringComparison.Ordinal);
        Assert.Contains("ON CONFLICT (user_id, workspace_id, symbol) DO UPDATE", sql, StringComparison.Ordinal);
        Assert.Contains("provider = CASE", sql, StringComparison.Ordinal);
        Assert.Contains("provider_symbol_id = COALESCE(EXCLUDED.provider_symbol_id", sql, StringComparison.Ordinal);
        Assert.Contains("ibkr_conid = COALESCE(EXCLUDED.ibkr_conid", sql, StringComparison.Ordinal);
        Assert.DoesNotContain("sort_order = EXCLUDED.sort_order", sql, StringComparison.Ordinal);
        Assert.Contains("updated_at_utc = EXCLUDED.updated_at_utc", sql, StringComparison.Ordinal);
    }

    [Fact]
    public void WorkspaceStatementsRemainScopedAndReturnStableOrdering()
    {
        Assert.Contains("WHERE user_id = @user_id", PostgresWorkspaceWatchlistSql.SelectByWorkspace, StringComparison.Ordinal);
        Assert.Contains("AND workspace_id = @workspace_id", PostgresWorkspaceWatchlistSql.SelectByWorkspace, StringComparison.Ordinal);
        Assert.Contains("ORDER BY sort_order ASC, symbol ASC", PostgresWorkspaceWatchlistSql.SelectByWorkspace, StringComparison.Ordinal);

        Assert.Contains("WHERE user_id = @user_id", PostgresWorkspaceWatchlistSql.DeletePinnedSymbol, StringComparison.Ordinal);
        Assert.Contains("AND workspace_id = @workspace_id", PostgresWorkspaceWatchlistSql.DeletePinnedSymbol, StringComparison.Ordinal);
        Assert.Contains("AND symbol = @symbol", PostgresWorkspaceWatchlistSql.DeletePinnedSymbol, StringComparison.Ordinal);

        Assert.Contains("WHERE user_id = @user_id", PostgresWorkspaceWatchlistSql.DeleteWorkspacePins, StringComparison.Ordinal);
        Assert.Contains("AND workspace_id = @workspace_id", PostgresWorkspaceWatchlistSql.DeleteWorkspacePins, StringComparison.Ordinal);

        Assert.Contains("@sort_order", PostgresWorkspaceWatchlistSql.InsertReplacementPinnedSymbol, StringComparison.Ordinal);
    }
}
