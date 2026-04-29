using ATrade.ServiceDefaults;
using Aspire.Hosting;
using Aspire.Hosting.JavaScript;

const string safeInfraContainerPidsLimit = "2048";
const string timescaleTuneMemory = "512MB";
const string timescaleTuneCpuCount = "2";

var localPortContract = LocalDevelopmentPortContractLoader.Load();
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

builder.AddProject<Projects.ATrade_Api>("api")
    .WithReference(postgres)
    .WithReference(timescaledb)
    .WithReference(redis)
    .WithReference(nats)
    .WithExternalHttpEndpoints();

builder.AddProject<Projects.ATrade_Ibkr_Worker>("ibkr-worker")
    .WithReference(postgres)
    .WithReference(redis)
    .WithReference(nats);

builder.AddJavaScriptApp("frontend", localPortContract.FrontendDirectory, "dev")
    .WithNpm()
    .WithEnvironment("NODE_ENV", "development")
    .WithHttpEndpoint(targetPort: localPortContract.AppHostFrontendHttpPort, env: "PORT")
    .WithExternalHttpEndpoints();

builder.Build().Run();
