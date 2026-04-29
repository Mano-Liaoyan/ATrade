using ATrade.Accounts;
using ATrade.ServiceDefaults;

var builder = WebApplication.CreateBuilder(args);

LocalDevelopmentPortContractLoader.ApplyApiHttpPortDefault(builder);
builder.AddServiceDefaults();
builder.Services.AddAccountsModule();

var app = builder.Build();

app.MapGet("/health", () => Results.Text("ok", "text/plain"));
app.MapGet("/api/accounts/overview", (IAccountOverviewProvider overviewProvider) => Results.Ok(overviewProvider.GetOverview()));

app.Run();
