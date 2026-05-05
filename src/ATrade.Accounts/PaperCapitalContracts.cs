namespace ATrade.Accounts;

public static class PaperCapitalSources
{
    public const string IbkrPaperBalance = "ibkr-paper-balance";
    public const string LocalPaperLedger = "local-paper-ledger";
    public const string Unavailable = "unavailable";
}

public static class PaperCapitalAvailabilityStates
{
    public const string Available = "available";
    public const string Disabled = "disabled";
    public const string CredentialsMissing = "credentials-missing";
    public const string Unauthenticated = "unauthenticated";
    public const string RejectedLive = "rejected-live";
    public const string Timeout = "timeout";
    public const string ProviderUnavailable = "provider-unavailable";
    public const string Error = "error";
    public const string Unconfigured = "unconfigured";
}

public static class PaperCapitalMessageSeverity
{
    public const string Info = "info";
    public const string Warning = "warning";
    public const string Error = "error";
}

public sealed record PaperCapitalMessage(
    string Code,
    string Message,
    string Severity = PaperCapitalMessageSeverity.Info);

public sealed record LocalPaperCapitalState(
    bool Configured,
    decimal? Capital,
    string Currency,
    DateTimeOffset? UpdatedAtUtc)
{
    public static LocalPaperCapitalState Unconfigured(string currency = LocalPaperCapitalValidator.DefaultCurrency) =>
        new(false, null, currency, null);
}

public sealed record IbkrPaperCapitalAvailability(
    bool Available,
    string State,
    decimal? Capital,
    string Currency,
    IReadOnlyList<PaperCapitalMessage> Messages)
{
    public static IbkrPaperCapitalAvailability Unavailable(
        string state,
        string code,
        string message,
        string currency = LocalPaperCapitalValidator.DefaultCurrency,
        string severity = PaperCapitalMessageSeverity.Warning) =>
        new(false, state, null, currency, [new PaperCapitalMessage(code, message, severity)]);
}

public sealed record PaperCapitalResponse(
    decimal? EffectiveCapital,
    string Currency,
    string Source,
    IbkrPaperCapitalAvailability IbkrAvailable,
    bool LocalConfigured,
    decimal? LocalCapital,
    IReadOnlyList<PaperCapitalMessage> Messages);

public sealed record LocalPaperCapitalUpdateRequest(decimal? Amount, string? Currency);

public sealed record PaperCapitalIntakeError(string Code, string Message);

public sealed record PaperCapitalIntakeResult(
    bool Succeeded,
    PaperCapitalResponse? Response,
    PaperCapitalIntakeError? Error)
{
    public static PaperCapitalIntakeResult Success(PaperCapitalResponse response) => new(true, response, null);

    public static PaperCapitalIntakeResult ValidationFailure(string code, string message) =>
        new(false, null, new PaperCapitalIntakeError(code, message));

    public static PaperCapitalIntakeResult StorageUnavailable() =>
        new(false, null, new PaperCapitalIntakeError(
            PaperCapitalErrorCodes.StorageUnavailable,
            PaperCapitalSafeMessages.LocalStorageUnavailable));
}

public interface IIbkrPaperCapitalProvider
{
    Task<IbkrPaperCapitalAvailability> GetAvailabilityAsync(CancellationToken cancellationToken = default);
}

public sealed class UnavailableIbkrPaperCapitalProvider : IIbkrPaperCapitalProvider
{
    public Task<IbkrPaperCapitalAvailability> GetAvailabilityAsync(CancellationToken cancellationToken = default) =>
        Task.FromResult(IbkrPaperCapitalAvailability.Unavailable(
            PaperCapitalAvailabilityStates.Disabled,
            PaperCapitalErrorCodes.IbkrDisabled,
            PaperCapitalSafeMessages.IbkrSourceUnavailable,
            severity: PaperCapitalMessageSeverity.Info));
}

public interface IPaperCapitalService
{
    Task<PaperCapitalResponse> GetAsync(CancellationToken cancellationToken = default);

    Task<PaperCapitalIntakeResult> UpdateLocalAsync(LocalPaperCapitalUpdateRequest? request, CancellationToken cancellationToken = default);
}
