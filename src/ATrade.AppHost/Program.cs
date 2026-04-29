using ATrade.AppHost;
using ATrade.Brokers.Ibkr;
using ATrade.ServiceDefaults;
using Aspire.Hosting;
using Aspire.Hosting.JavaScript;

const string safeInfraContainerPidsLimit = "2048";
const string timescaleTuneMemory = "512MB";
const string timescaleTuneCpuCount = "2";

var localPortContract = LocalDevelopmentPortContractLoader.Load();
var paperTradingContract = PaperTradingEnvironmentContract.Load(localPortContract.LoadedFromPath);
var builder = DistributedApplication.CreateBuilder(args);

var postgres = builder.AddPostgres("postgres")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit);

// TimescaleDB runs the Postgres protocol, so model it as a dedicated Postgres server
// resource that uses the TimescaleDB container image in the local Aspire graph.
var timescaledb = builder.AddPostgres("timescaledb")
    .WithImage("timescale/timescaledb", "latest-pg17")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit)
    .WithEnvironment("TS_TUNE_MEMORY", timescaleTuneMemory)
    .WithEnvironment("TS_TUNE_NUM_CPUS", timescaleTuneCpuCount);

var redis = builder.AddRedis("redis")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit);
var nats = builder.AddNats("nats")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit);

if (paperTradingContract.TryGetGatewayImageReference(out var gatewayImage, out var gatewayTag))
{
    builder.AddContainer("ibkr-gateway", gatewayImage, gatewayTag)
        .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit)
        .WithHttpEndpoint(
            targetPort: paperTradingContract.GetGatewayPort(),
            port: paperTradingContract.GetGatewayPort(),
            isProxied: false);
}

var api = builder.AddProject<Projects.ATrade_Api>("api")
    .WithReference(postgres)
    .WithReference(timescaledb)
    .WithReference(redis)
    .WithReference(nats)
    .WithExternalHttpEndpoints()
    .WithEnvironment(IbkrGatewayEnvironmentVariables.IntegrationEnabled, paperTradingContract.BrokerIntegrationEnabled)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.AccountMode, paperTradingContract.BrokerAccountMode)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayUrl, paperTradingContract.GatewayUrl)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayPort, paperTradingContract.GatewayPort)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayImage, paperTradingContract.GatewayImage)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.PaperAccountId, paperTradingContract.PaperAccountId);

var ibkrWorker = builder.AddProject<Projects.ATrade_Ibkr_Worker>("ibkr-worker")
    .WithReference(postgres)
    .WithReference(redis)
    .WithReference(nats)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.IntegrationEnabled, paperTradingContract.BrokerIntegrationEnabled)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.AccountMode, paperTradingContract.BrokerAccountMode)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayUrl, paperTradingContract.GatewayUrl)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayPort, paperTradingContract.GatewayPort)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayImage, paperTradingContract.GatewayImage)
    .WithEnvironment(IbkrGatewayEnvironmentVariables.PaperAccountId, paperTradingContract.PaperAccountId);

if (!string.IsNullOrWhiteSpace(paperTradingContract.GatewayTimeoutSeconds))
{
    api.WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayTimeoutSeconds, paperTradingContract.GatewayTimeoutSeconds);
    ibkrWorker.WithEnvironment(IbkrGatewayEnvironmentVariables.GatewayTimeoutSeconds, paperTradingContract.GatewayTimeoutSeconds);
}

var frontendApiBaseUrl = $"http://127.0.0.1:{localPortContract.ApiHttpPort}";

builder.AddJavaScriptApp("frontend", localPortContract.FrontendDirectory, "dev")
    .WithNpm()
    .WithEnvironment("NODE_ENV", "development")
    .WithEnvironment("ATRADE_FRONTEND_API_BASE_URL", frontendApiBaseUrl)
    .WithEnvironment("NEXT_PUBLIC_ATRADE_API_BASE_URL", frontendApiBaseUrl)
    .WithHttpEndpoint(targetPort: localPortContract.AppHostFrontendHttpPort, env: "PORT")
    .WithExternalHttpEndpoints();

builder.Build().Run();
