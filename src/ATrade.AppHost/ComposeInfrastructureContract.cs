using System.Globalization;
using ATrade.ServiceDefaults;
using Aspire.Hosting.ApplicationModel;

namespace ATrade.AppHost;

public sealed record ComposeInfrastructureContract(
    string Mode,
    int PostgresPort,
    int TimescaleDbPort,
    int RedisPort,
    int NatsPort)
{
    private const string ComposeDatabaseUsername = "atrade";
    private const string ComposePostgresDatabase = "atrade";
    private const string ComposeTimescaleDatabase = "atrade_marketdata";

    public bool IsEnabled => string.Equals(Mode, LocalRuntimeInfrastructureSettings.ComposeMode, StringComparison.OrdinalIgnoreCase);

    public static ComposeInfrastructureContract Load(LocalRuntimeContract runtimeContract)
    {
        ArgumentNullException.ThrowIfNull(runtimeContract);

        return new ComposeInfrastructureContract(
            runtimeContract.Infrastructure.Mode,
            runtimeContract.Ports.PostgresPort,
            runtimeContract.Ports.TimescaleDbPort,
            runtimeContract.Ports.RedisPort,
            runtimeContract.Ports.NatsPort);
    }

    public ReferenceExpression BuildPostgresConnectionString(IResourceBuilder<ParameterResource> password) =>
        BuildPostgresProtocolConnectionString(PostgresPort, ComposePostgresDatabase, password);

    public ReferenceExpression BuildTimescaleConnectionString(IResourceBuilder<ParameterResource> password) =>
        BuildPostgresProtocolConnectionString(TimescaleDbPort, ComposeTimescaleDatabase, password);

    public string BuildRedisConnectionString() => $"127.0.0.1:{RedisPort}";

    public string BuildNatsConnectionString() => $"nats://127.0.0.1:{NatsPort}";

    private static ReferenceExpression BuildPostgresProtocolConnectionString(
        int port,
        string database,
        IResourceBuilder<ParameterResource> password)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(database);
        ArgumentNullException.ThrowIfNull(password);

        var portText = port.ToString(CultureInfo.InvariantCulture);
        var prefix = $"Host=127.0.0.1;Port={portText};Username={ComposeDatabaseUsername};Password=";
        var suffix = $";Database={database}";

        return ReferenceExpression.Create($"{prefix}{password}{suffix}");
    }
}
