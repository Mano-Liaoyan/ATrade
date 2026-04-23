using Aspire.Hosting;
using Aspire.Hosting.JavaScript;

var builder = DistributedApplication.CreateBuilder(args);

builder.AddPostgres("postgres");

// TimescaleDB runs the Postgres protocol, so model it as a dedicated Postgres server
// resource that uses the TimescaleDB container image in the local Aspire graph.
builder.AddPostgres("timescaledb")
    .WithImage("timescale/timescaledb", "latest-pg17");

builder.AddRedis("redis");
builder.AddNats("nats");

builder.AddProject<Projects.ATrade_Api>("api")
    .WithExternalHttpEndpoints();

builder.AddJavaScriptApp("frontend", "../../frontend", "dev")
    .WithNpm()
    .WithHttpEndpoint(targetPort: 3000, env: "PORT")
    .WithExternalHttpEndpoints();

builder.Build().Run();
