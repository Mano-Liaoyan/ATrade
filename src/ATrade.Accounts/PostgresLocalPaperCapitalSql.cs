namespace ATrade.Accounts;

internal static class PostgresLocalPaperCapitalSql
{
    public const string SchemaName = "atrade_accounts";
    public const string LocalPaperCapitalTableName = "local_paper_capital";
    public const string QualifiedLocalPaperCapitalTableName = SchemaName + "." + LocalPaperCapitalTableName;

    public const string Initialize = """
        CREATE SCHEMA IF NOT EXISTS atrade_accounts;

        CREATE TABLE IF NOT EXISTS atrade_accounts.local_paper_capital (
            user_id text NOT NULL,
            workspace_id text NOT NULL,
            amount numeric(19, 2) NOT NULL,
            currency text NOT NULL DEFAULT 'USD',
            created_at_utc timestamptz NOT NULL DEFAULT now(),
            updated_at_utc timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT pk_local_paper_capital PRIMARY KEY (user_id, workspace_id),
            CONSTRAINT ck_local_paper_capital_amount_positive CHECK (amount > 0),
            CONSTRAINT ck_local_paper_capital_currency CHECK (currency IN ('USD'))
        );

        ALTER TABLE atrade_accounts.local_paper_capital
            ADD COLUMN IF NOT EXISTS amount numeric(19, 2) NOT NULL DEFAULT 100000.00;
        ALTER TABLE atrade_accounts.local_paper_capital
            ADD COLUMN IF NOT EXISTS currency text NOT NULL DEFAULT 'USD';
        ALTER TABLE atrade_accounts.local_paper_capital
            ADD COLUMN IF NOT EXISTS created_at_utc timestamptz NOT NULL DEFAULT now();
        ALTER TABLE atrade_accounts.local_paper_capital
            ADD COLUMN IF NOT EXISTS updated_at_utc timestamptz NOT NULL DEFAULT now();

        ALTER TABLE atrade_accounts.local_paper_capital
            DROP CONSTRAINT IF EXISTS ck_local_paper_capital_amount_positive;
        ALTER TABLE atrade_accounts.local_paper_capital
            ADD CONSTRAINT ck_local_paper_capital_amount_positive CHECK (amount > 0);

        ALTER TABLE atrade_accounts.local_paper_capital
            DROP CONSTRAINT IF EXISTS ck_local_paper_capital_currency;
        ALTER TABLE atrade_accounts.local_paper_capital
            ADD CONSTRAINT ck_local_paper_capital_currency CHECK (currency IN ('USD'));

        CREATE INDEX IF NOT EXISTS ix_local_paper_capital_workspace_updated
            ON atrade_accounts.local_paper_capital (user_id, workspace_id, updated_at_utc DESC);
        """;

    public const string SelectByWorkspace = """
        SELECT amount,
               currency,
               updated_at_utc
          FROM atrade_accounts.local_paper_capital
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id;
        """;

    public const string UpsertLocalPaperCapital = """
        INSERT INTO atrade_accounts.local_paper_capital (
            user_id,
            workspace_id,
            amount,
            currency,
            created_at_utc,
            updated_at_utc)
        VALUES (
            @user_id,
            @workspace_id,
            @amount,
            @currency,
            @observed_at_utc,
            @observed_at_utc)
        ON CONFLICT (user_id, workspace_id) DO UPDATE
            SET amount = EXCLUDED.amount,
                currency = EXCLUDED.currency,
                updated_at_utc = EXCLUDED.updated_at_utc
        RETURNING amount,
                  currency,
                  updated_at_utc;
        """;
}
