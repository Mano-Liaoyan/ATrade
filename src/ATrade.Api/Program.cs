using ATrade.ServiceDefaults;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

var app = builder.Build();

app.MapGet("/health", () => Results.Text("ok", "text/plain"));

app.Run();
