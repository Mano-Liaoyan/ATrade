using System.Text.Json;
using Microsoft.AspNetCore.SignalR;

namespace ATrade.Backtesting;

public static class BacktestRunUpdateEvents
{
    public const string RunCreated = "backtestRunCreated";
    public const string StatusChanged = "backtestRunStatusChanged";
    public const string RunCompleted = "backtestRunCompleted";
    public const string RunFailed = "backtestRunFailed";
    public const string RunCancelled = "backtestRunCancelled";

    public static string ForRunStatus(string status) => status switch
    {
        var value when string.Equals(value, BacktestRunStatuses.Completed, StringComparison.OrdinalIgnoreCase) => RunCompleted,
        var value when string.Equals(value, BacktestRunStatuses.Failed, StringComparison.OrdinalIgnoreCase) => RunFailed,
        var value when string.Equals(value, BacktestRunStatuses.Cancelled, StringComparison.OrdinalIgnoreCase) => RunCancelled,
        _ => StatusChanged,
    };
}

public sealed class BacktestRunsHub : Hub;

public interface IBacktestRunUpdatePublisher
{
    Task PublishAsync(string eventName, BacktestRunEnvelope run, CancellationToken cancellationToken = default);
}

public sealed class SignalRBacktestRunUpdatePublisher(IHubContext<BacktestRunsHub> hubContext) : IBacktestRunUpdatePublisher
{
    public Task PublishAsync(string eventName, BacktestRunEnvelope run, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(eventName);
        ArgumentNullException.ThrowIfNull(run);

        var payload = BacktestRunUpdatePayload.From(eventName, run);
        return hubContext.Clients.All.SendAsync(eventName, payload, cancellationToken);
    }
}

public sealed record BacktestRunUpdatePayload(
    string Event,
    string Id,
    string Status,
    string? SourceRunId,
    BacktestRunUpdateSymbolPayload Symbol,
    string StrategyId,
    string? EngineId,
    string ChartRange,
    DateTimeOffset CreatedAtUtc,
    DateTimeOffset UpdatedAtUtc,
    DateTimeOffset? StartedAtUtc,
    DateTimeOffset? CompletedAtUtc,
    BacktestError? Error,
    JsonElement? Result)
{
    public static BacktestRunUpdatePayload From(string eventName, BacktestRunEnvelope run)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(eventName);
        ArgumentNullException.ThrowIfNull(run);

        var safeError = BacktestPersistenceSafety.NormalizeSafeError(run.Error);
        var safeResult = NormalizeSafeResult(run.Result);

        return new BacktestRunUpdatePayload(
            eventName,
            run.Id,
            run.Status,
            run.SourceRunId,
            new BacktestRunUpdateSymbolPayload(
                run.Request.Symbol.Symbol,
                run.Request.Symbol.Provider,
                run.Request.Symbol.ProviderSymbolId,
                run.Request.Symbol.AssetClass,
                run.Request.Symbol.Exchange,
                run.Request.Symbol.Currency),
            run.Request.StrategyId,
            run.Request.EngineId,
            run.Request.ChartRange,
            run.CreatedAtUtc,
            run.UpdatedAtUtc,
            run.StartedAtUtc,
            run.CompletedAtUtc,
            safeError,
            safeResult);
    }

    private static JsonElement? NormalizeSafeResult(JsonElement? result)
    {
        var serializedResult = BacktestPersistenceSafety.SerializeResult(result);
        return serializedResult is null
            ? null
            : BacktestPersistenceSafety.DeserializeResult(serializedResult);
    }
}

public sealed record BacktestRunUpdateSymbolPayload(
    string Symbol,
    string Provider,
    string? ProviderSymbolId,
    string AssetClass,
    string Exchange,
    string Currency);
