namespace ATrade.Workspaces;

public interface IWorkspaceWatchlistIntake
{
    Task<WorkspaceWatchlistIntakeResult> GetAsync(CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistIntakeResult> ReplaceAsync(ReplaceWorkspaceWatchlistRequest? request, CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistIntakeResult> PinAsync(WorkspaceWatchlistSymbolInput? symbol, CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistIntakeResult> UnpinByInstrumentKeyAsync(string? instrumentKey, CancellationToken cancellationToken = default);

    Task<WorkspaceWatchlistIntakeResult> UnpinBySymbolAsync(string? symbol, CancellationToken cancellationToken = default);
}

public enum WorkspaceWatchlistIntakeErrorKind
{
    Validation,
    StorageUnavailable,
}

public sealed record ReplaceWorkspaceWatchlistRequest(IReadOnlyList<WorkspaceWatchlistSymbolInput>? Symbols);

public sealed record WorkspaceWatchlistIntakeError(
    string Code,
    string Error,
    WorkspaceWatchlistIntakeErrorKind Kind);

public sealed record WorkspaceWatchlistIntakeResult(
    WorkspaceWatchlistResponse? Response,
    WorkspaceWatchlistIntakeError? Error)
{
    public bool IsSuccess => Response is not null;

    public static WorkspaceWatchlistIntakeResult Success(WorkspaceWatchlistResponse response)
    {
        ArgumentNullException.ThrowIfNull(response);
        return new WorkspaceWatchlistIntakeResult(response, null);
    }

    public static WorkspaceWatchlistIntakeResult ValidationFailure(string code, string error) => new(
        null,
        new WorkspaceWatchlistIntakeError(code, error, WorkspaceWatchlistIntakeErrorKind.Validation));

    public static WorkspaceWatchlistIntakeResult StorageUnavailable(string code, string error) => new(
        null,
        new WorkspaceWatchlistIntakeError(code, error, WorkspaceWatchlistIntakeErrorKind.StorageUnavailable));
}

/// <summary>
/// Coordinates watchlist requests inside the Workspaces module. The temporary
/// local-paper identity seam is deliberately consumed here, not in the HTTP API,
/// so a future authenticated workspace resolver can replace
/// <see cref="IWorkspaceIdentityProvider" /> without changing route handlers.
/// </summary>
public sealed class WorkspaceWatchlistIntake(
    IWorkspaceIdentityProvider identityProvider,
    IWorkspaceWatchlistSchemaInitializer schemaInitializer,
    IWorkspaceWatchlistRepository repository) : IWorkspaceWatchlistIntake
{
    public Task<WorkspaceWatchlistIntakeResult> GetAsync(CancellationToken cancellationToken = default) =>
        ExecuteAsync(identity => repository.GetAsync(identity, cancellationToken), cancellationToken);

    public async Task<WorkspaceWatchlistIntakeResult> ReplaceAsync(
        ReplaceWorkspaceWatchlistRequest? request,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var symbols = NormalizeReplacementWatchlistRequest(request);
            return await ExecuteAsync(identity => repository.ReplaceAsync(identity, symbols, cancellationToken), cancellationToken).ConfigureAwait(false);
        }
        catch (WorkspaceWatchlistValidationException exception)
        {
            return ToValidationFailure(exception);
        }
    }

    public async Task<WorkspaceWatchlistIntakeResult> PinAsync(
        WorkspaceWatchlistSymbolInput? symbol,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var normalizedSymbol = NormalizePinnedSymbolRequest(symbol);
            return await ExecuteAsync(identity => repository.PinAsync(identity, normalizedSymbol, cancellationToken), cancellationToken).ConfigureAwait(false);
        }
        catch (WorkspaceWatchlistValidationException exception)
        {
            return ToValidationFailure(exception);
        }
    }

    public async Task<WorkspaceWatchlistIntakeResult> UnpinByInstrumentKeyAsync(
        string? instrumentKey,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var normalizedInstrumentKey = WorkspaceWatchlistInstrumentKey.NormalizeExistingKey(instrumentKey);
            return await ExecuteAsync(identity => repository.UnpinByInstrumentKeyAsync(identity, normalizedInstrumentKey, cancellationToken), cancellationToken).ConfigureAwait(false);
        }
        catch (WorkspaceWatchlistValidationException exception)
        {
            return ToValidationFailure(exception);
        }
    }

    public async Task<WorkspaceWatchlistIntakeResult> UnpinBySymbolAsync(
        string? symbol,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var normalizedSymbol = WorkspaceSymbolNormalizer.Normalize(symbol ?? string.Empty);
            return await ExecuteAsync(identity => repository.UnpinAsync(identity, normalizedSymbol, cancellationToken), cancellationToken).ConfigureAwait(false);
        }
        catch (WorkspaceWatchlistValidationException exception)
        {
            return ToValidationFailure(exception);
        }
    }

    private async Task<WorkspaceWatchlistIntakeResult> ExecuteAsync(
        Func<WorkspaceIdentity, Task<WorkspaceWatchlistResponse>> operation,
        CancellationToken cancellationToken)
    {
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            var identity = identityProvider.Current;
            await schemaInitializer.InitializeAsync(cancellationToken).ConfigureAwait(false);
            var response = await operation(identity).ConfigureAwait(false);
            return WorkspaceWatchlistIntakeResult.Success(response);
        }
        catch (WorkspaceWatchlistValidationException exception)
        {
            return ToValidationFailure(exception);
        }
        catch (WorkspaceStorageUnavailableException exception)
        {
            return WorkspaceWatchlistIntakeResult.StorageUnavailable(exception.Code, "Watchlist storage is unavailable.");
        }
    }

    private static WorkspaceWatchlistIntakeResult ToValidationFailure(WorkspaceWatchlistValidationException exception) =>
        WorkspaceWatchlistIntakeResult.ValidationFailure(exception.Code, exception.Message);

    private static WorkspaceWatchlistSymbolInput NormalizePinnedSymbolRequest(WorkspaceWatchlistSymbolInput? symbol)
    {
        if (symbol is null)
        {
            throw new WorkspaceWatchlistValidationException(
                WorkspaceWatchlistErrorCodes.InvalidSymbol,
                "A watchlist symbol payload is required.");
        }

        var normalized = WorkspaceWatchlistNormalizer.Normalize(symbol);
        return ToSymbolInput(normalized);
    }

    private static IReadOnlyList<WorkspaceWatchlistSymbolInput> NormalizeReplacementWatchlistRequest(ReplaceWorkspaceWatchlistRequest? request)
    {
        var symbols = request?.Symbols ?? Array.Empty<WorkspaceWatchlistSymbolInput>();
        return WorkspaceWatchlistNormalizer.NormalizeReplacement(symbols)
            .Select(ToSymbolInput)
            .ToArray();
    }

    private static WorkspaceWatchlistSymbolInput ToSymbolInput(NormalizedWorkspaceWatchlistSymbolInput symbol) => new(
        symbol.Symbol,
        symbol.Provider,
        symbol.ProviderSymbolId,
        symbol.IbkrConid,
        symbol.Name,
        symbol.Exchange,
        symbol.Currency,
        symbol.AssetClass);
}
