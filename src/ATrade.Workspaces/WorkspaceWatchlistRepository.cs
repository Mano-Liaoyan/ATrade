namespace ATrade.Workspaces;

public interface IWorkspaceWatchlistSchemaInitializer
{
    Task InitializeAsync(CancellationToken cancellationToken = default);
}

public interface IWorkspaceWatchlistRepository
{
    Task<WorkspaceWatchlistResponse> GetAsync(WorkspaceIdentity identity, CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistResponse> PinAsync(
        WorkspaceIdentity identity,
        WorkspaceWatchlistSymbolInput symbol,
        CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistResponse> ReplaceAsync(
        WorkspaceIdentity identity,
        IReadOnlyList<WorkspaceWatchlistSymbolInput> symbols,
        CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistResponse> UnpinAsync(
        WorkspaceIdentity identity,
        string symbol,
        CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistResponse> UnpinByInstrumentKeyAsync(
        WorkspaceIdentity identity,
        string instrumentKey,
        CancellationToken cancellationToken = default);
}

public sealed class WorkspaceStorageUnavailableException : InvalidOperationException
{
    public WorkspaceStorageUnavailableException(string message, Exception? innerException = null)
        : base(message, innerException)
    {
    }

    public string Code => WorkspaceWatchlistErrorCodes.StorageUnavailable;
}
