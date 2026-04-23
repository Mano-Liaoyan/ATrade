using ATrade.Ibkr.Worker;
using ATrade.ServiceDefaults;

var builder = Host.CreateApplicationBuilder(args);
builder.AddServiceDefaults();
builder.Services.AddHostedService<IbkrWorkerShell>();

var host = builder.Build();
host.Run();
