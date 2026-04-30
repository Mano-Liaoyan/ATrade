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
            instrument_key text NOT NULL,
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
            CONSTRAINT pk_workspace_watchlist_pins PRIMARY KEY (user_id, workspace_id, instrument_key)
        );

        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'manual';
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS provider_symbol_id text NULL;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS ibkr_conid bigint NULL;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS name text NULL;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS exchange text NULL;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS currency text NULL;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS asset_class text NULL;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS sort_order integer NOT NULL DEFAULT 0;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS created_at_utc timestamptz NOT NULL DEFAULT now();
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS updated_at_utc timestamptz NOT NULL DEFAULT now();
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD COLUMN IF NOT EXISTS instrument_key text NULL;

        UPDATE atrade_workspaces.workspace_watchlist_pins
           SET instrument_key = concat_ws(
                   '|',
                   'provider=' || lower(COALESCE(NULLIF(btrim(provider), ''), 'manual')),
                   'providerSymbolId=' || COALESCE(NULLIF(btrim(provider_symbol_id), ''), ''),
                   'ibkrConid=' || COALESCE(ibkr_conid::text, ''),
                   'symbol=' || upper(symbol),
                   'exchange=' || upper(COALESCE(NULLIF(btrim(exchange), ''), '')),
                   'currency=' || upper(COALESCE(NULLIF(btrim(currency), ''), 'USD')),
                   'assetClass=' || upper(COALESCE(NULLIF(btrim(asset_class), ''), 'STK')))
         WHERE instrument_key IS NULL
            OR btrim(instrument_key) = '';

        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ALTER COLUMN instrument_key SET NOT NULL;

        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            DROP CONSTRAINT IF EXISTS pk_workspace_watchlist_pins;
        ALTER TABLE atrade_workspaces.workspace_watchlist_pins
            ADD CONSTRAINT pk_workspace_watchlist_pins PRIMARY KEY (user_id, workspace_id, instrument_key);

        CREATE INDEX IF NOT EXISTS ix_workspace_watchlist_pins_workspace_order
            ON atrade_workspaces.workspace_watchlist_pins (user_id, workspace_id, sort_order, symbol, instrument_key);
        CREATE INDEX IF NOT EXISTS ix_workspace_watchlist_pins_workspace_symbol
            ON atrade_workspaces.workspace_watchlist_pins (user_id, workspace_id, symbol);
        """;

    public const string SelectByWorkspace = """
        SELECT symbol,
               instrument_key,
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
         ORDER BY sort_order ASC, symbol ASC, instrument_key ASC;
        """;

    public const string UpsertPinnedSymbol = """
        WITH next_sort_order AS (
            SELECT COALESCE(
                (SELECT sort_order
                   FROM atrade_workspaces.workspace_watchlist_pins
                  WHERE user_id = @user_id
                    AND workspace_id = @workspace_id
                    AND instrument_key = @instrument_key),
                (SELECT COALESCE(MAX(sort_order) + 1, 0)
                   FROM atrade_workspaces.workspace_watchlist_pins
                  WHERE user_id = @user_id
                    AND workspace_id = @workspace_id)
            ) AS value
        )
        INSERT INTO atrade_workspaces.workspace_watchlist_pins (
            user_id,
            workspace_id,
            instrument_key,
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
               @instrument_key,
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
        ON CONFLICT (user_id, workspace_id, instrument_key) DO UPDATE
            SET symbol = EXCLUDED.symbol,
                provider = EXCLUDED.provider,
                provider_symbol_id = COALESCE(EXCLUDED.provider_symbol_id, atrade_workspaces.workspace_watchlist_pins.provider_symbol_id),
                ibkr_conid = COALESCE(EXCLUDED.ibkr_conid, atrade_workspaces.workspace_watchlist_pins.ibkr_conid),
                name = COALESCE(EXCLUDED.name, atrade_workspaces.workspace_watchlist_pins.name),
                exchange = COALESCE(EXCLUDED.exchange, atrade_workspaces.workspace_watchlist_pins.exchange),
                currency = COALESCE(EXCLUDED.currency, atrade_workspaces.workspace_watchlist_pins.currency),
                asset_class = COALESCE(EXCLUDED.asset_class, atrade_workspaces.workspace_watchlist_pins.asset_class),
                updated_at_utc = EXCLUDED.updated_at_utc;
        """;

    public const string DeletePinnedInstrumentKey = """
        DELETE FROM atrade_workspaces.workspace_watchlist_pins
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id
           AND instrument_key = @instrument_key;
        """;

    public const string DeletePinnedSymbol = """
        WITH candidates AS (
            SELECT instrument_key
              FROM atrade_workspaces.workspace_watchlist_pins
             WHERE user_id = @user_id
               AND workspace_id = @workspace_id
               AND symbol = @symbol
        ),
        deleted AS (
            DELETE FROM atrade_workspaces.workspace_watchlist_pins pins
             WHERE pins.user_id = @user_id
               AND pins.workspace_id = @workspace_id
               AND pins.instrument_key IN (SELECT instrument_key FROM candidates)
               AND (SELECT COUNT(*) FROM candidates) = 1
             RETURNING 1
        )
        SELECT (SELECT COUNT(*) FROM candidates)::integer AS candidate_count,
               (SELECT COUNT(*) FROM deleted)::integer AS deleted_count;
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
            instrument_key,
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
            @instrument_key,
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
