using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace ATrade.ServiceDefaults;

public static class Extensions
{
    public static WebApplicationBuilder AddServiceDefaults(this WebApplicationBuilder builder)
    {
        builder.Services.AddHealthChecks();

        return builder;
    }

    public static HostApplicationBuilder AddServiceDefaults(this HostApplicationBuilder builder)
    {
        builder.Services.AddHealthChecks();

        return builder;
    }
}
