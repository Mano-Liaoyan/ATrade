namespace ATrade.Workspaces;

internal static class PostgresWorkspaceWatchlistSql
{
    public const string SchemaName = "atrade_workspaces";
    public const string WatchlistPinsTableName = "workspace_watchlist_pins";
    public const string QualifiedWatchlistPinsTableName = SchemaName + "." + WatchlistPinsTableName;

    public const string Initialize = """
        CREATE SCHEMA IF NOT EXISTS atrade_workspaces;

        CREATE TABLE IF NOT EXISTS atrade_workspaces.workspace_watchlist_pins (
            user_id text NOT NULL,
            workspace_id text NOT NULL,
            symbol text NOT NULL,
            provider text NOT NULL DEFAULT 'manual',
            provider_symbol_id text NULL,
            ibkr_conid bigint NULL,
            name text NULL,
            exchange text NULL,
            currency text NULL,
            asset_class text NULL,
            sort_order integer NOT NULL DEFAULT 0,
            created_at_utc timestamptz NOT NULL DEFAULT now(),
            updated_at_utc timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT pk_workspace_watchlist_pins PRIMARY KEY (user_id, workspace_id, symbol)
        );

        CREATE INDEX IF NOT EXISTS ix_workspace_watchlist_pins_workspace_order
            ON atrade_workspaces.workspace_watchlist_pins (user_id, workspace_id, sort_order, symbol);
        """;

    public const string SelectByWorkspace = """
        SELECT symbol,
               provider,
               provider_symbol_id,
               ibkr_conid,
               name,
               exchange,
               currency,
               asset_class,
               sort_order,
               created_at_utc,
               updated_at_utc
          FROM atrade_workspaces.workspace_watchlist_pins
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id
         ORDER BY sort_order ASC, symbol ASC;
        """;

    public const string UpsertPinnedSymbol = """
        WITH deleted_provider_duplicate AS (
            DELETE FROM atrade_workspaces.workspace_watchlist_pins
             WHERE user_id = @user_id
               AND workspace_id = @workspace_id
               AND symbol <> @symbol
               AND provider = @provider
               AND (
                   (@provider_symbol_id IS NOT NULL AND provider_symbol_id = @provider_symbol_id)
                   OR (@ibkr_conid IS NOT NULL AND ibkr_conid = @ibkr_conid)
               )
             RETURNING sort_order
        ),
        next_sort_order AS (
            SELECT COALESCE(
                (SELECT MIN(sort_order) FROM deleted_provider_duplicate),
                (SELECT sort_order
                   FROM atrade_workspaces.workspace_watchlist_pins
                  WHERE user_id = @user_id
                    AND workspace_id = @workspace_id
                    AND symbol = @symbol),
                (SELECT COALESCE(MAX(sort_order) + 1, 0)
                   FROM atrade_workspaces.workspace_watchlist_pins
                  WHERE user_id = @user_id
                    AND workspace_id = @workspace_id)
            ) AS value
        )
        INSERT INTO atrade_workspaces.workspace_watchlist_pins (
            user_id,
            workspace_id,
            symbol,
            provider,
            provider_symbol_id,
            ibkr_conid,
            name,
            exchange,
            currency,
            asset_class,
            sort_order,
            created_at_utc,
            updated_at_utc)
        SELECT @user_id,
               @workspace_id,
               @symbol,
               @provider,
               @provider_symbol_id,
               @ibkr_conid,
               @name,
               @exchange,
               @currency,
               @asset_class,
               value,
               @observed_at_utc,
               @observed_at_utc
          FROM next_sort_order
        ON CONFLICT (user_id, workspace_id, symbol) DO UPDATE
            SET provider = CASE
                    WHEN EXCLUDED.provider <> 'manual'
                         OR EXCLUDED.provider_symbol_id IS NOT NULL
                         OR EXCLUDED.ibkr_conid IS NOT NULL
                    THEN EXCLUDED.provider
                    ELSE atrade_workspaces.workspace_watchlist_pins.provider
                END,
                provider_symbol_id = COALESCE(EXCLUDED.provider_symbol_id, atrade_workspaces.workspace_watchlist_pins.provider_symbol_id),
                ibkr_conid = COALESCE(EXCLUDED.ibkr_conid, atrade_workspaces.workspace_watchlist_pins.ibkr_conid),
                name = COALESCE(EXCLUDED.name, atrade_workspaces.workspace_watchlist_pins.name),
                exchange = COALESCE(EXCLUDED.exchange, atrade_workspaces.workspace_watchlist_pins.exchange),
                currency = COALESCE(EXCLUDED.currency, atrade_workspaces.workspace_watchlist_pins.currency),
                asset_class = COALESCE(EXCLUDED.asset_class, atrade_workspaces.workspace_watchlist_pins.asset_class),
                updated_at_utc = EXCLUDED.updated_at_utc;
        """;

    public const string DeletePinnedSymbol = """
        DELETE FROM atrade_workspaces.workspace_watchlist_pins
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id
           AND symbol = @symbol;
        """;

    public const string DeleteWorkspacePins = """
        DELETE FROM atrade_workspaces.workspace_watchlist_pins
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id;
        """;

    public const string InsertReplacementPinnedSymbol = """
        INSERT INTO atrade_workspaces.workspace_watchlist_pins (
            user_id,
            workspace_id,
            symbol,
            provider,
            provider_symbol_id,
            ibkr_conid,
            name,
            exchange,
            currency,
            asset_class,
            sort_order,
            created_at_utc,
            updated_at_utc)
        VALUES (
            @user_id,
            @workspace_id,
            @symbol,
            @provider,
            @provider_symbol_id,
            @ibkr_conid,
            @name,
            @exchange,
            @currency,
            @asset_class,
            @sort_order,
            @observed_at_utc,
            @observed_at_utc);
        """;
}
