using Npgsql;
using NpgsqlTypes;

namespace ATrade.Accounts;

public sealed class PostgresLocalPaperCapitalRepository(IAccountsPostgresDataSourceProvider dataSourceProvider, TimeProvider timeProvider) : ILocalPaperCapitalRepository
{
    public PostgresLocalPaperCapitalRepository(IAccountsPostgresDataSourceProvider dataSourceProvider)
        : this(dataSourceProvider, TimeProvider.System)
    {
    }

    public async Task<LocalPaperCapitalState> GetAsync(PaperCapitalIdentity identity, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(identity);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresLocalPaperCapitalSql.SelectByWorkspace);
            AddIdentityParameters(command, identity);

            await using var reader = await command.ExecuteReaderAsync(cancellationToken);
            if (!await reader.ReadAsync(cancellationToken))
            {
                return LocalPaperCapitalState.Unconfigured();
            }

            return ReadState(reader);
        }
        catch (NpgsqlException exception)
        {
            throw new PaperCapitalStorageUnavailableException("Postgres local paper capital read failed.", exception);
        }
    }

    public async Task<LocalPaperCapitalState> UpsertAsync(
        PaperCapitalIdentity identity,
        LocalPaperCapitalValue value,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(identity);
        ArgumentNullException.ThrowIfNull(value);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresLocalPaperCapitalSql.UpsertLocalPaperCapital);
            AddIdentityParameters(command, identity);
            command.Parameters.AddWithValue("amount", NpgsqlDbType.Numeric, value.Amount);
            command.Parameters.AddWithValue("currency", NpgsqlDbType.Text, value.Currency);
            command.Parameters.AddWithValue("observed_at_utc", NpgsqlDbType.TimestampTz, timeProvider.GetUtcNow());

            await using var reader = await command.ExecuteReaderAsync(cancellationToken);
            if (await reader.ReadAsync(cancellationToken))
            {
                return ReadState(reader);
            }
        }
        catch (NpgsqlException exception)
        {
            throw new PaperCapitalStorageUnavailableException("Postgres local paper capital update failed.", exception);
        }

        return await GetAsync(identity, cancellationToken);
    }

    private static void AddIdentityParameters(NpgsqlCommand command, PaperCapitalIdentity identity)
    {
        command.Parameters.AddWithValue("user_id", NpgsqlDbType.Text, identity.UserId);
        command.Parameters.AddWithValue("workspace_id", NpgsqlDbType.Text, identity.WorkspaceId);
    }

    private static LocalPaperCapitalState ReadState(NpgsqlDataReader reader) => new(
        Configured: true,
        Capital: reader.GetDecimal(0),
        Currency: reader.GetString(1),
        UpdatedAtUtc: reader.GetFieldValue<DateTimeOffset>(2));
}
