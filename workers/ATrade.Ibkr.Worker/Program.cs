using ATrade.Brokers.Ibkr;
using ATrade.Ibkr.Worker;
using ATrade.ServiceDefaults;

var builder = Host.CreateApplicationBuilder(args);
builder.AddServiceDefaults();
builder.Services.AddIbkrBrokerAdapter(builder.Configuration);
builder.Services.AddHostedService<IbkrWorkerShell>();

var host = builder.Build();
host.Run();
