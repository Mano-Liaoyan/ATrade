using Aspire.Hosting;
using Aspire.Hosting.JavaScript;

var builder = DistributedApplication.CreateBuilder(args);

builder.AddProject<Projects.ATrade_Api>("api")
    .WithExternalHttpEndpoints();

builder.AddJavaScriptApp("frontend", "../../frontend", "dev")
    .WithNpm()
    .WithHttpEndpoint(targetPort: 3000, env: "PORT")
    .WithExternalHttpEndpoints();

builder.Build().Run();
