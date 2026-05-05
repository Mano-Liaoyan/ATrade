namespace ATrade.Accounts;

public sealed class PaperCapitalService(
    ILocalPaperCapitalRepository localRepository,
    IPaperCapitalIdentityProvider identityProvider,
    ILocalPaperCapitalSchemaInitializer schemaInitializer,
    IEnumerable<IIbkrPaperCapitalProvider> ibkrPaperCapitalProviders) : IPaperCapitalService
{
    public async Task<PaperCapitalResponse> GetAsync(CancellationToken cancellationToken = default)
    {
        var ibkrAvailability = await GetBestIbkrAvailabilityAsync(cancellationToken).ConfigureAwait(false);
        var localState = await GetLocalStateOrUnavailableAsync(cancellationToken).ConfigureAwait(false);

        return BuildResponse(ibkrAvailability, localState.State, localState.StorageAvailable);
    }

    public async Task<PaperCapitalIntakeResult> UpdateLocalAsync(
        LocalPaperCapitalUpdateRequest? request,
        CancellationToken cancellationToken = default)
    {
        LocalPaperCapitalValue value;
        try
        {
            value = LocalPaperCapitalValidator.Validate(request);
        }
        catch (PaperCapitalValidationException exception)
        {
            return PaperCapitalIntakeResult.ValidationFailure(exception.Code, exception.Message);
        }

        var identity = identityProvider.Current;
        try
        {
            await schemaInitializer.InitializeAsync(cancellationToken).ConfigureAwait(false);
            await localRepository.UpsertAsync(identity, value, cancellationToken).ConfigureAwait(false);
        }
        catch (PaperCapitalStorageUnavailableException)
        {
            return PaperCapitalIntakeResult.StorageUnavailable();
        }

        return PaperCapitalIntakeResult.Success(await GetAsync(cancellationToken).ConfigureAwait(false));
    }

    private async Task<IbkrPaperCapitalAvailability> GetBestIbkrAvailabilityAsync(CancellationToken cancellationToken)
    {
        IbkrPaperCapitalAvailability? bestUnavailable = null;

        foreach (var provider in ibkrPaperCapitalProviders)
        {
            IbkrPaperCapitalAvailability availability;
            try
            {
                availability = PaperCapitalRedaction.Redact(await provider.GetAvailabilityAsync(cancellationToken).ConfigureAwait(false));
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                throw;
            }
            catch
            {
                availability = IbkrPaperCapitalAvailability.Unavailable(
                    PaperCapitalAvailabilityStates.Error,
                    PaperCapitalErrorCodes.IbkrUnavailable,
                    PaperCapitalSafeMessages.IbkrSourceUnavailable,
                    severity: PaperCapitalMessageSeverity.Warning);
            }

            if (IsUsableIbkrCapital(availability))
            {
                return availability;
            }

            bestUnavailable ??= availability;
        }

        return bestUnavailable ?? IbkrPaperCapitalAvailability.Unavailable(
            PaperCapitalAvailabilityStates.Disabled,
            PaperCapitalErrorCodes.IbkrDisabled,
            PaperCapitalSafeMessages.IbkrSourceUnavailable,
            severity: PaperCapitalMessageSeverity.Info);
    }

    private async Task<(LocalPaperCapitalState State, bool StorageAvailable)> GetLocalStateOrUnavailableAsync(CancellationToken cancellationToken)
    {
        try
        {
            await schemaInitializer.InitializeAsync(cancellationToken).ConfigureAwait(false);
            return (await localRepository.GetAsync(identityProvider.Current, cancellationToken).ConfigureAwait(false), true);
        }
        catch (PaperCapitalStorageUnavailableException)
        {
            return (LocalPaperCapitalState.Unconfigured(), false);
        }
    }

    private static PaperCapitalResponse BuildResponse(
        IbkrPaperCapitalAvailability ibkrAvailability,
        LocalPaperCapitalState localState,
        bool localStorageAvailable)
    {
        var messages = new List<PaperCapitalMessage>();
        messages.AddRange(ibkrAvailability.Messages);

        if (IsUsableIbkrCapital(ibkrAvailability))
        {
            if (!localStorageAvailable)
            {
                messages.Add(new PaperCapitalMessage(
                    PaperCapitalErrorCodes.StorageUnavailable,
                    PaperCapitalSafeMessages.LocalStorageUnavailable,
                    PaperCapitalMessageSeverity.Warning));
            }

            return new PaperCapitalResponse(
                EffectiveCapital: ibkrAvailability.Capital,
                Currency: ibkrAvailability.Currency,
                Source: PaperCapitalSources.IbkrPaperBalance,
                IbkrAvailable: ibkrAvailability,
                LocalConfigured: localState.Configured,
                LocalCapital: localState.Capital,
                Messages: messages);
        }

        if (localStorageAvailable && localState.Configured && localState.Capital.HasValue)
        {
            return new PaperCapitalResponse(
                EffectiveCapital: localState.Capital,
                Currency: localState.Currency,
                Source: PaperCapitalSources.LocalPaperLedger,
                IbkrAvailable: ibkrAvailability,
                LocalConfigured: true,
                LocalCapital: localState.Capital,
                Messages: messages);
        }

        messages.Add(localStorageAvailable
            ? new PaperCapitalMessage(
                PaperCapitalErrorCodes.LocalUnconfigured,
                PaperCapitalSafeMessages.LocalSourceUnconfigured,
                PaperCapitalMessageSeverity.Info)
            : new PaperCapitalMessage(
                PaperCapitalErrorCodes.StorageUnavailable,
                PaperCapitalSafeMessages.LocalStorageUnavailable,
                PaperCapitalMessageSeverity.Warning));
        messages.Add(new PaperCapitalMessage(
            PaperCapitalErrorCodes.NoCapitalSource,
            PaperCapitalSafeMessages.NoCapitalSource,
            PaperCapitalMessageSeverity.Warning));

        return new PaperCapitalResponse(
            EffectiveCapital: null,
            Currency: localState.Currency,
            Source: PaperCapitalSources.Unavailable,
            IbkrAvailable: ibkrAvailability,
            LocalConfigured: false,
            LocalCapital: null,
            Messages: messages);
    }

    private static bool IsUsableIbkrCapital(IbkrPaperCapitalAvailability availability) =>
        availability.Available &&
        availability.Capital.HasValue &&
        availability.Capital.Value > 0 &&
        string.Equals(availability.State, PaperCapitalAvailabilityStates.Available, StringComparison.Ordinal);
}
