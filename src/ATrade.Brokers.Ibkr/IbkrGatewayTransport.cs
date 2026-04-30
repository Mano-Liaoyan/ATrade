using System.Net;
using System.Net.Http;
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;

namespace ATrade.Brokers.Ibkr;

public static class IbkrGatewayTransport
{
    public const string DefaultLoopbackGatewayUrl = "https://127.0.0.1:5000";
    public const string RequiredLoopbackScheme = "https";

    public static Uri DefaultGatewayBaseUri { get; } = new(DefaultLoopbackGatewayUrl, UriKind.Absolute);

    public static Uri CreateDefaultGatewayBaseUri(int? port = null)
    {
        if (port is > 0 and <= 65535 and not 5000)
        {
            return new UriBuilder(DefaultGatewayBaseUri)
            {
                Port = port.Value,
            }.Uri;
        }

        return DefaultGatewayBaseUri;
    }

    public static Uri NormalizeGatewayBaseUri(Uri gatewayBaseUri, IbkrGatewayContainerOptions gatewayContainer)
    {
        ArgumentNullException.ThrowIfNull(gatewayBaseUri);
        ArgumentNullException.ThrowIfNull(gatewayContainer);

        if (gatewayContainer.IsIbeamImage && IsLoopbackHost(gatewayBaseUri.Host) && string.Equals(gatewayBaseUri.Scheme, Uri.UriSchemeHttp, StringComparison.OrdinalIgnoreCase))
        {
            return new UriBuilder(gatewayBaseUri)
            {
                Scheme = Uri.UriSchemeHttps,
                Port = gatewayBaseUri.IsDefaultPort ? -1 : gatewayBaseUri.Port,
            }.Uri;
        }

        return gatewayBaseUri;
    }

    public static void ConfigureHttpClient(HttpClient client, IbkrGatewayOptions options)
    {
        ArgumentNullException.ThrowIfNull(client);
        ArgumentNullException.ThrowIfNull(options);

        client.Timeout = options.RequestTimeout;
        if (options.GatewayBaseUrl is not null)
        {
            client.BaseAddress = options.GatewayBaseUrl;
        }
    }

    public static HttpMessageHandler CreateHttpMessageHandler(IbkrGatewayOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);

        return new HttpClientHandler
        {
            ServerCertificateCustomValidationCallback = (request, certificate, chain, sslPolicyErrors) =>
                ValidateLocalIbeamCertificate(options, request, certificate, chain, sslPolicyErrors),
        };
    }

    public static bool ValidateLocalIbeamCertificate(
        IbkrGatewayOptions options,
        HttpRequestMessage? request,
        X509Certificate2? certificate,
        X509Chain? chain,
        SslPolicyErrors sslPolicyErrors)
    {
        ArgumentNullException.ThrowIfNull(options);

        if (sslPolicyErrors == SslPolicyErrors.None)
        {
            return true;
        }

        if (certificate is null || request?.RequestUri is null || options.GatewayBaseUrl is null)
        {
            return false;
        }

        if (!IsLocalIbeamHttpsRequest(options, request.RequestUri))
        {
            return false;
        }

        if ((sslPolicyErrors & ~(SslPolicyErrors.RemoteCertificateChainErrors | SslPolicyErrors.RemoteCertificateNameMismatch)) != 0)
        {
            return false;
        }

        return IsSelfSignedCertificate(certificate, chain);
    }

    public static bool IsLocalIbeamHttpsRequest(IbkrGatewayOptions options, Uri requestUri)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentNullException.ThrowIfNull(requestUri);

        return options.GatewayContainer.IsIbeamImage &&
            options.GatewayBaseUrl is not null &&
            string.Equals(options.GatewayBaseUrl.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(requestUri.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase) &&
            IsLoopbackHost(options.GatewayBaseUrl.Host) &&
            IsLoopbackHost(requestUri.Host) &&
            PortsMatch(options.GatewayBaseUrl, requestUri);
    }

    public static string CreateTransportUnavailableMessage() =>
        "IBKR iBeam is configured but the local Client Portal HTTPS transport is not reachable. Verify the gateway URL uses https for the local iBeam port, authenticate the paper iBeam session, and retry.";

    public static string CreateTransportTimeoutMessage() =>
        "IBKR iBeam local Client Portal HTTPS transport timed out. Verify iBeam is running and authenticated, then retry.";

    public static bool IsLoopbackHost(string host)
    {
        if (string.Equals(host, "localhost", StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        return IPAddress.TryParse(host, out var address) && IPAddress.IsLoopback(address);
    }

    private static bool PortsMatch(Uri gatewayBaseUri, Uri requestUri)
    {
        var gatewayPort = gatewayBaseUri.IsDefaultPort ? DefaultPortForScheme(gatewayBaseUri.Scheme) : gatewayBaseUri.Port;
        var requestPort = requestUri.IsDefaultPort ? DefaultPortForScheme(requestUri.Scheme) : requestUri.Port;
        return gatewayPort == requestPort;
    }

    private static int DefaultPortForScheme(string scheme) => string.Equals(scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase) ? 443 : 80;

    private static bool IsSelfSignedCertificate(X509Certificate2 certificate, X509Chain? chain)
    {
        if (!string.Equals(certificate.Subject, certificate.Issuer, StringComparison.Ordinal))
        {
            return false;
        }

        return chain is null ||
            chain.ChainElements.Count <= 1 ||
            chain.ChainElements.Cast<X509ChainElement>().All(element => string.Equals(element.Certificate.Thumbprint, certificate.Thumbprint, StringComparison.OrdinalIgnoreCase));
    }
}
