namespace ATrade.Backtesting;

internal static class PostgresBacktestRunSql
{
    public const string SchemaName = "atrade_backtesting";
    public const string RunsTableName = "saved_backtest_runs";
    public const string QualifiedRunsTableName = SchemaName + "." + RunsTableName;

    private const string SelectRunColumns = """
            user_id,
            workspace_id,
            run_id,
            source_run_id,
            status,
            request_json::text,
            initial_capital,
            currency,
            capital_source,
            error_code,
            error_message,
            result_json::text,
            created_at_utc,
            updated_at_utc,
            started_at_utc,
            completed_at_utc
        """;

    public const string Initialize = """
        CREATE SCHEMA IF NOT EXISTS atrade_backtesting;

        CREATE TABLE IF NOT EXISTS atrade_backtesting.saved_backtest_runs (
            user_id text NOT NULL,
            workspace_id text NOT NULL,
            run_id text NOT NULL,
            source_run_id text NULL,
            status text NOT NULL,
            request_json jsonb NOT NULL,
            initial_capital numeric(19, 2) NOT NULL,
            currency text NOT NULL DEFAULT 'USD',
            capital_source text NOT NULL,
            error_code text NULL,
            error_message text NULL,
            result_json jsonb NULL,
            created_at_utc timestamptz NOT NULL DEFAULT now(),
            updated_at_utc timestamptz NOT NULL DEFAULT now(),
            started_at_utc timestamptz NULL,
            completed_at_utc timestamptz NULL,
            CONSTRAINT pk_saved_backtest_runs PRIMARY KEY (user_id, workspace_id, run_id),
            CONSTRAINT ck_saved_backtest_runs_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
            CONSTRAINT ck_saved_backtest_runs_initial_capital_positive CHECK (initial_capital > 0),
            CONSTRAINT ck_saved_backtest_runs_currency CHECK (currency IN ('USD')),
            CONSTRAINT ck_saved_backtest_runs_request_json_object CHECK (jsonb_typeof(request_json) = 'object')
        );

        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS source_run_id text NULL;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'queued';
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS request_json jsonb NOT NULL DEFAULT '{}'::jsonb;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS initial_capital numeric(19, 2) NOT NULL DEFAULT 100000.00;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS currency text NOT NULL DEFAULT 'USD';
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS capital_source text NOT NULL DEFAULT 'local-paper-ledger';
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS error_code text NULL;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS error_message text NULL;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS result_json jsonb NULL;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS created_at_utc timestamptz NOT NULL DEFAULT now();
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS updated_at_utc timestamptz NOT NULL DEFAULT now();
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS started_at_utc timestamptz NULL;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD COLUMN IF NOT EXISTS completed_at_utc timestamptz NULL;

        ALTER TABLE atrade_backtesting.saved_backtest_runs
            DROP CONSTRAINT IF EXISTS ck_saved_backtest_runs_status;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD CONSTRAINT ck_saved_backtest_runs_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'));

        ALTER TABLE atrade_backtesting.saved_backtest_runs
            DROP CONSTRAINT IF EXISTS ck_saved_backtest_runs_initial_capital_positive;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD CONSTRAINT ck_saved_backtest_runs_initial_capital_positive CHECK (initial_capital > 0);

        ALTER TABLE atrade_backtesting.saved_backtest_runs
            DROP CONSTRAINT IF EXISTS ck_saved_backtest_runs_currency;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD CONSTRAINT ck_saved_backtest_runs_currency CHECK (currency IN ('USD'));

        ALTER TABLE atrade_backtesting.saved_backtest_runs
            DROP CONSTRAINT IF EXISTS ck_saved_backtest_runs_request_json_object;
        ALTER TABLE atrade_backtesting.saved_backtest_runs
            ADD CONSTRAINT ck_saved_backtest_runs_request_json_object CHECK (jsonb_typeof(request_json) = 'object');

        CREATE INDEX IF NOT EXISTS ix_saved_backtest_runs_workspace_created
            ON atrade_backtesting.saved_backtest_runs (user_id, workspace_id, created_at_utc DESC, run_id DESC);
        CREATE INDEX IF NOT EXISTS ix_saved_backtest_runs_workspace_status
            ON atrade_backtesting.saved_backtest_runs (user_id, workspace_id, status, updated_at_utc DESC);
        """;

    public const string InsertRun = """
        INSERT INTO atrade_backtesting.saved_backtest_runs (
            user_id,
            workspace_id,
            run_id,
            source_run_id,
            status,
            request_json,
            initial_capital,
            currency,
            capital_source,
            error_code,
            error_message,
            result_json,
            created_at_utc,
            updated_at_utc,
            started_at_utc,
            completed_at_utc)
        VALUES (
            @user_id,
            @workspace_id,
            @run_id,
            @source_run_id,
            @status,
            @request_json,
            @initial_capital,
            @currency,
            @capital_source,
            @error_code,
            @error_message,
            @result_json,
            @created_at_utc,
            @updated_at_utc,
            @started_at_utc,
            @completed_at_utc)
        RETURNING
        """ + SelectRunColumns + """
        ;
        """;

    public const string SelectByWorkspace = """
        SELECT
        """ + SelectRunColumns + """
          FROM atrade_backtesting.saved_backtest_runs
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id
         ORDER BY created_at_utc DESC, run_id DESC
         LIMIT @limit;
        """;

    public const string SelectByRunId = """
        SELECT
        """ + SelectRunColumns + """
          FROM atrade_backtesting.saved_backtest_runs
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id
           AND run_id = @run_id;
        """;

    public const string FailInterruptedRunningRuns = """
        UPDATE atrade_backtesting.saved_backtest_runs
           SET status = 'failed',
               error_code = @error_code,
               error_message = @error_message,
               updated_at_utc = @observed_at_utc,
               completed_at_utc = COALESCE(completed_at_utc, @observed_at_utc)
         WHERE status = 'running';
        """;

    public const string ClaimNextQueuedRun = """
        WITH next_queued_run AS (
            SELECT user_id,
                   workspace_id,
                   run_id
              FROM atrade_backtesting.saved_backtest_runs
             WHERE status = 'queued'
             ORDER BY created_at_utc ASC, run_id ASC
             FOR UPDATE SKIP LOCKED
             LIMIT 1
        )
        UPDATE atrade_backtesting.saved_backtest_runs AS run
           SET status = 'running',
               error_code = NULL,
               error_message = NULL,
               result_json = NULL,
               updated_at_utc = @observed_at_utc,
               started_at_utc = COALESCE(started_at_utc, @observed_at_utc),
               completed_at_utc = NULL
          FROM next_queued_run
         WHERE run.user_id = next_queued_run.user_id
           AND run.workspace_id = next_queued_run.workspace_id
           AND run.run_id = next_queued_run.run_id
           AND run.status = 'queued'
        RETURNING
        """ + SelectRunColumns + """
        ;
        """;

    public const string UpdateStatus = """
        UPDATE atrade_backtesting.saved_backtest_runs
           SET status = @status,
               error_code = @error_code,
               error_message = @error_message,
               result_json = COALESCE(@result_json, result_json),
               updated_at_utc = @observed_at_utc,
               started_at_utc = CASE
                   WHEN @status = 'running' THEN COALESCE(started_at_utc, @observed_at_utc)
                   ELSE started_at_utc
               END,
               completed_at_utc = CASE
                   WHEN @status IN ('completed', 'failed', 'cancelled') THEN COALESCE(completed_at_utc, @observed_at_utc)
                   WHEN @status IN ('queued', 'running') THEN NULL
                   ELSE completed_at_utc
               END
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id
           AND run_id = @run_id
           AND (status = 'running' OR @status = 'running')
        RETURNING
        """ + SelectRunColumns + """
        ;
        """;

    public const string CancelRun = """
        UPDATE atrade_backtesting.saved_backtest_runs
           SET status = 'cancelled',
               error_code = NULL,
               error_message = NULL,
               updated_at_utc = @observed_at_utc,
               completed_at_utc = COALESCE(completed_at_utc, @observed_at_utc)
         WHERE user_id = @user_id
           AND workspace_id = @workspace_id
           AND run_id = @run_id
           AND status IN ('queued', 'running')
        RETURNING
        """ + SelectRunColumns + """
        ;
        """;

    public const string InsertRetryRun = """
        WITH retry_source AS (
            SELECT request_json
              FROM atrade_backtesting.saved_backtest_runs
             WHERE user_id = @user_id
               AND workspace_id = @workspace_id
               AND run_id = @source_run_id
               AND status IN ('failed', 'cancelled')
        )
        INSERT INTO atrade_backtesting.saved_backtest_runs (
            user_id,
            workspace_id,
            run_id,
            source_run_id,
            status,
            request_json,
            initial_capital,
            currency,
            capital_source,
            error_code,
            error_message,
            result_json,
            created_at_utc,
            updated_at_utc,
            started_at_utc,
            completed_at_utc)
        SELECT @user_id,
               @workspace_id,
               @run_id,
               @source_run_id,
               'queued',
               request_json,
               @initial_capital,
               @currency,
               @capital_source,
               NULL,
               NULL,
               NULL,
               @created_at_utc,
               @updated_at_utc,
               NULL,
               NULL
          FROM retry_source
        RETURNING
        """ + SelectRunColumns + """
        ;
        """;
}
