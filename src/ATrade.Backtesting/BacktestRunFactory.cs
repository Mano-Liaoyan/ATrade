using ATrade.Accounts;

namespace ATrade.Backtesting;

public interface IBacktestRunFactory
{
    Task<BacktestCreateResult> CreateQueuedRunAsync(BacktestCreateRequest? request, CancellationToken cancellationToken = default);
}

public sealed class BacktestRunFactory(
    IPaperCapitalService paperCapitalService,
    IPaperCapitalIdentityProvider identityProvider,
    TimeProvider timeProvider) : IBacktestRunFactory
{
    public BacktestRunFactory(IPaperCapitalService paperCapitalService, IPaperCapitalIdentityProvider identityProvider)
        : this(paperCapitalService, identityProvider, TimeProvider.System)
    {
    }

    public async Task<BacktestCreateResult> CreateQueuedRunAsync(
        BacktestCreateRequest? request,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        BacktestRequestSnapshot requestSnapshot;
        try
        {
            requestSnapshot = BacktestRequestValidator.Validate(request);
        }
        catch (BacktestValidationException exception)
        {
            return BacktestCreateResult.Failure(exception.Code, exception.Message);
        }

        PaperCapitalResponse capitalResponse;
        try
        {
            capitalResponse = await paperCapitalService.GetAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            return BacktestCreateResult.Failure(BacktestErrorCodes.CapitalUnavailable, BacktestSafeMessages.CapitalUnavailable);
        }

        if (!TryCreateCapitalSnapshot(capitalResponse, out var capitalSnapshot))
        {
            return BacktestCreateResult.Failure(BacktestErrorCodes.CapitalUnavailable, BacktestSafeMessages.CapitalUnavailable);
        }

        var observedAtUtc = timeProvider.GetUtcNow();
        var run = new BacktestRunEnvelope(
            Id: BacktestRunId.New().Value,
            Status: BacktestRunStatuses.Queued,
            Request: requestSnapshot,
            Capital: capitalSnapshot,
            CreatedAtUtc: observedAtUtc,
            UpdatedAtUtc: observedAtUtc,
            StartedAtUtc: null,
            CompletedAtUtc: null,
            Error: null,
            Result: null);

        var scope = BacktestWorkspaceScope.From(identityProvider.Current);
        return BacktestCreateResult.Success(new BacktestRunRecord(scope, run));
    }

    private static bool TryCreateCapitalSnapshot(PaperCapitalResponse capitalResponse, out BacktestCapitalSnapshot snapshot)
    {
        snapshot = new BacktestCapitalSnapshot(0m, BacktestDefaults.Currency, PaperCapitalSources.Unavailable);

        if (!capitalResponse.EffectiveCapital.HasValue || capitalResponse.EffectiveCapital.Value <= 0)
        {
            return false;
        }

        if (string.Equals(capitalResponse.Source, PaperCapitalSources.Unavailable, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        snapshot = new BacktestCapitalSnapshot(
            decimal.Round(capitalResponse.EffectiveCapital.Value, 2, MidpointRounding.AwayFromZero),
            string.IsNullOrWhiteSpace(capitalResponse.Currency) ? BacktestDefaults.Currency : capitalResponse.Currency.Trim().ToUpperInvariant(),
            capitalResponse.Source.Trim());
        return true;
    }
}
