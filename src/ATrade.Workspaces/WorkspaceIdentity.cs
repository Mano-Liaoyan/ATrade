namespace ATrade.Workspaces;

public sealed record WorkspaceIdentity(string UserId, string WorkspaceId)
{
    public static WorkspaceIdentity Create(string userId, string workspaceId)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(userId);
        ArgumentException.ThrowIfNullOrWhiteSpace(workspaceId);

        return new WorkspaceIdentity(userId.Trim(), workspaceId.Trim());
    }
}

public interface IWorkspaceIdentityProvider
{
    WorkspaceIdentity Current { get; }
}

/// <summary>
/// Temporary no-auth identity provider for the local paper-trading workspace.
/// Replace this implementation with the authenticated user/workspace resolver when
/// authentication and named workspaces are introduced; repository rows already carry
/// both ids so that migration should not require a schema rewrite.
/// </summary>
public sealed class LocalWorkspaceIdentityProvider : IWorkspaceIdentityProvider
{
    public WorkspaceIdentity Current { get; } = WorkspaceIdentityDefaults.LocalPaperTradingWorkspace;
}

public static class WorkspaceIdentityDefaults
{
    public const string LocalUserId = "local-user";
    public const string PaperTradingWorkspaceId = "paper-trading";

    // Temporary seam until authentication and named workspaces exist. All watchlist
    // endpoints deliberately flow through IWorkspaceIdentityProvider so auth can
    // replace this local-only identity without changing repository storage shape.
    public static WorkspaceIdentity LocalPaperTradingWorkspace { get; } = WorkspaceIdentity.Create(LocalUserId, PaperTradingWorkspaceId);
}
