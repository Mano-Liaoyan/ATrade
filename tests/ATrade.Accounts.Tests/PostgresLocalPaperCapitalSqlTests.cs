using ATrade.Accounts;

namespace ATrade.Accounts.Tests;

public sealed class PostgresLocalPaperCapitalSqlTests
{
    [Fact]
    public void Initialize_IsIdempotentScopedAndRejectsInvalidStoredValues()
    {
        var sql = PostgresLocalPaperCapitalSql.Initialize;

        Assert.Contains("CREATE SCHEMA IF NOT EXISTS atrade_accounts", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE TABLE IF NOT EXISTS atrade_accounts.local_paper_capital", sql, StringComparison.Ordinal);
        Assert.Contains("user_id text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("workspace_id text NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("amount numeric(19, 2) NOT NULL", sql, StringComparison.Ordinal);
        Assert.Contains("currency text NOT NULL DEFAULT 'USD'", sql, StringComparison.Ordinal);
        Assert.Contains("PRIMARY KEY (user_id, workspace_id)", sql, StringComparison.Ordinal);
        Assert.Contains("CHECK (amount > 0)", sql, StringComparison.Ordinal);
        Assert.Contains("CHECK (currency IN ('USD'))", sql, StringComparison.Ordinal);
        Assert.Contains("ADD COLUMN IF NOT EXISTS amount", sql, StringComparison.Ordinal);
        Assert.Contains("DROP CONSTRAINT IF EXISTS ck_local_paper_capital_amount_positive", sql, StringComparison.Ordinal);
        Assert.Contains("CREATE INDEX IF NOT EXISTS ix_local_paper_capital_workspace_updated", sql, StringComparison.Ordinal);
    }

    [Fact]
    public void Statements_AreScopedToTemporaryLocalUserAndWorkspaceKeysWithoutProviderAccountColumns()
    {
        Assert.Contains("WHERE user_id = @user_id", PostgresLocalPaperCapitalSql.SelectByWorkspace, StringComparison.Ordinal);
        Assert.Contains("AND workspace_id = @workspace_id", PostgresLocalPaperCapitalSql.SelectByWorkspace, StringComparison.Ordinal);
        Assert.Contains("@amount", PostgresLocalPaperCapitalSql.UpsertLocalPaperCapital, StringComparison.Ordinal);
        Assert.Contains("@currency", PostgresLocalPaperCapitalSql.UpsertLocalPaperCapital, StringComparison.Ordinal);
        Assert.Contains("ON CONFLICT (user_id, workspace_id) DO UPDATE", PostgresLocalPaperCapitalSql.UpsertLocalPaperCapital, StringComparison.Ordinal);
        Assert.Contains("RETURNING amount", PostgresLocalPaperCapitalSql.UpsertLocalPaperCapital, StringComparison.Ordinal);

        Assert.DoesNotContain("account_id", PostgresLocalPaperCapitalSql.Initialize, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("credential", PostgresLocalPaperCapitalSql.Initialize, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", PostgresLocalPaperCapitalSql.Initialize, StringComparison.OrdinalIgnoreCase);
    }
}
