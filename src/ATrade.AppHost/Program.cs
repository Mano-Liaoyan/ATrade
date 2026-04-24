using Aspire.Hosting;
using Aspire.Hosting.JavaScript;

const string safeInfraContainerPidsLimit = "2048";

var builder = DistributedApplication.CreateBuilder(args);

builder.AddPostgres("postgres")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit);

// TimescaleDB runs the Postgres protocol, so model it as a dedicated Postgres server
// resource that uses the TimescaleDB container image in the local Aspire graph.
builder.AddPostgres("timescaledb")
    .WithImage("timescale/timescaledb", "latest-pg17")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit);

builder.AddRedis("redis")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit);
builder.AddNats("nats")
    .WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit);

builder.AddProject<Projects.ATrade_Api>("api")
    .WithExternalHttpEndpoints();

builder.AddJavaScriptApp("frontend", "../../frontend", "dev")
    .WithNpm()
    .WithEnvironment("NODE_ENV", "development")
    .WithHttpEndpoint(targetPort: 3000, env: "PORT")
    .WithExternalHttpEndpoints();

builder.Build().Run();
