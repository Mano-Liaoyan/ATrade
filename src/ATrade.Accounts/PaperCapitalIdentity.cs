namespace ATrade.Accounts;

public sealed record PaperCapitalIdentity(string UserId, string WorkspaceId)
{
    public static PaperCapitalIdentity Create(string userId, string workspaceId)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(userId);
        ArgumentException.ThrowIfNullOrWhiteSpace(workspaceId);

        return new PaperCapitalIdentity(userId.Trim(), workspaceId.Trim());
    }
}

public interface IPaperCapitalIdentityProvider
{
    PaperCapitalIdentity Current { get; }
}

/// <summary>
/// Temporary no-auth identity provider for the local paper-trading workspace.
/// This mirrors the current workspace preference scope so paper capital rows can
/// later move behind authenticated users/workspaces without a storage rewrite.
/// </summary>
public sealed class LocalPaperCapitalIdentityProvider : IPaperCapitalIdentityProvider
{
    public PaperCapitalIdentity Current { get; } = PaperCapitalIdentityDefaults.LocalPaperTradingWorkspace;
}

public static class PaperCapitalIdentityDefaults
{
    public const string LocalUserId = "local-user";
    public const string PaperTradingWorkspaceId = "paper-trading";

    public static PaperCapitalIdentity LocalPaperTradingWorkspace { get; } =
        PaperCapitalIdentity.Create(LocalUserId, PaperTradingWorkspaceId);
}
