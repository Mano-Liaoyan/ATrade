namespace ATrade.Accounts;

public interface ILocalPaperCapitalSchemaInitializer
{
    Task InitializeAsync(CancellationToken cancellationToken = default);
}

public interface ILocalPaperCapitalRepository
{
    Task<LocalPaperCapitalState> GetAsync(PaperCapitalIdentity identity, CancellationToken cancellationToken = default);

    Task<LocalPaperCapitalState> UpsertAsync(
        PaperCapitalIdentity identity,
        LocalPaperCapitalValue value,
        CancellationToken cancellationToken = default);
}

public sealed class PaperCapitalStorageUnavailableException : InvalidOperationException
{
    public PaperCapitalStorageUnavailableException(string message, Exception? innerException = null)
        : base(message, innerException)
    {
    }

    public string Code => PaperCapitalErrorCodes.StorageUnavailable;
}
