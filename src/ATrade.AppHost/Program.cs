using Aspire.Hosting;
using Aspire.Hosting.JavaScript;

var builder = DistributedApplication.CreateBuilder(args);

builder.AddJavaScriptApp("frontend", "../../frontend", "dev")
    .WithNpm()
    .WithHttpEndpoint(targetPort: 3000, env: "PORT")
    .WithExternalHttpEndpoints();

builder.Build().Run();
