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

    public string BuildPostgresConnectionString(IResourceBuilder<ParameterResource> password) =>
        BuildPostgresProtocolConnectionString(PostgresPort, password);

    public string BuildTimescaleConnectionString(IResourceBuilder<ParameterResource> password) =>
        BuildPostgresProtocolConnectionString(TimescaleDbPort, password);

    public string BuildRedisConnectionString() => $"127.0.0.1:{RedisPort}";

    public string BuildNatsConnectionString() => $"nats://127.0.0.1:{NatsPort}";

    private static string BuildPostgresProtocolConnectionString(
        int port,
        IResourceBuilder<ParameterResource> password)
    {
        ArgumentNullException.ThrowIfNull(password);

        return $"Host=127.0.0.1;Port={port};Username=postgres;Password={{{password.Resource.Name}.value}};Database=postgres";
    }
}
