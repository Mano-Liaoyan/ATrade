using System.Net.Security;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using ATrade.Brokers.Ibkr;
using Microsoft.Extensions.Configuration;

namespace ATrade.Brokers.Ibkr.Tests;

public sealed class IbkrGatewayTransportContractTests
{
    [Fact]
    public void FromConfiguration_DefaultsToHttpsLoopbackIbeamGateway()
    {
        var options = IbkrGatewayOptions.FromConfiguration(new ConfigurationBuilder().Build());

        Assert.Equal(new Uri("https://127.0.0.1:5000"), options.GatewayBaseUrl);
    }

    [Fact]
    public void FromConfiguration_NormalizesLegacyHttpLoopbackIbeamUrlToHttps()
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    [IbkrGatewayEnvironmentVariables.IntegrationEnabled] = "true",
                    [IbkrGatewayEnvironmentVariables.AccountMode] = nameof(IbkrAccountMode.Paper),
                    [IbkrGatewayEnvironmentVariables.GatewayUrl] = "http://127.0.0.1:5000",
                    [IbkrGatewayEnvironmentVariables.GatewayPort] = "5000",
                    [IbkrGatewayEnvironmentVariables.GatewayImage] = IbkrGatewayContainerOptions.DefaultIbeamImage,
                })
            .Build();

        var options = IbkrGatewayOptions.FromConfiguration(configuration);

        Assert.Equal(new Uri("https://127.0.0.1:5000"), options.GatewayBaseUrl);
    }

    [Fact]
    public void FromConfiguration_DoesNotNormalizeNonLoopbackHttpGatewayUrls()
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    [IbkrGatewayEnvironmentVariables.GatewayUrl] = "http://gateway.paper.local:5000",
                    [IbkrGatewayEnvironmentVariables.GatewayPort] = "5000",
                    [IbkrGatewayEnvironmentVariables.GatewayImage] = IbkrGatewayContainerOptions.DefaultIbeamImage,
                })
            .Build();

        var options = IbkrGatewayOptions.FromConfiguration(configuration);

        Assert.Equal(new Uri("http://gateway.paper.local:5000"), options.GatewayBaseUrl);
    }

    [Fact]
    public void ConfigureHttpClient_SendsClientPortalCompatibleUserAgent()
    {
        var options = CreateOptions("https://127.0.0.1:5000", IbkrGatewayContainerOptions.DefaultIbeamImage);
        using var httpClient = new HttpClient();

        IbkrGatewayTransport.ConfigureHttpClient(httpClient, options);

        Assert.Equal(options.GatewayBaseUrl, httpClient.BaseAddress);
        Assert.Equal(options.RequestTimeout, httpClient.Timeout);
        Assert.Contains(
            httpClient.DefaultRequestHeaders.UserAgent,
            value => string.Equals(value.ToString(), IbkrGatewayTransport.ClientPortalUserAgent, StringComparison.Ordinal));
    }

    [Fact]
    public void ValidateLocalIbeamCertificate_AllowsSelfSignedCertificateOnlyForLoopbackIbeamHttps()
    {
        using var certificate = CreateSelfSignedCertificate();
        using var loopbackRequest = new HttpRequestMessage(HttpMethod.Get, "https://127.0.0.1:5000/v1/api/iserver/auth/status");
        using var remoteRequest = new HttpRequestMessage(HttpMethod.Get, "https://gateway.paper.local:5000/v1/api/iserver/auth/status");
        using var httpRequest = new HttpRequestMessage(HttpMethod.Get, "http://127.0.0.1:5000/v1/api/iserver/auth/status");
        var loopbackOptions = CreateOptions("https://127.0.0.1:5000", IbkrGatewayContainerOptions.DefaultIbeamImage);
        var nonIbeamOptions = CreateOptions("https://127.0.0.1:5000", "example.invalid/ibkr-gateway-paper:local");

        Assert.True(IbkrGatewayTransport.ValidateLocalIbeamCertificate(
            loopbackOptions,
            loopbackRequest,
            certificate,
            chain: null,
            SslPolicyErrors.RemoteCertificateChainErrors));
        Assert.True(IbkrGatewayTransport.ValidateLocalIbeamCertificate(
            loopbackOptions,
            loopbackRequest,
            certificate,
            chain: null,
            SslPolicyErrors.RemoteCertificateChainErrors | SslPolicyErrors.RemoteCertificateNameMismatch));
        Assert.False(IbkrGatewayTransport.ValidateLocalIbeamCertificate(
            loopbackOptions,
            remoteRequest,
            certificate,
            chain: null,
            SslPolicyErrors.RemoteCertificateChainErrors));
        Assert.False(IbkrGatewayTransport.ValidateLocalIbeamCertificate(
            loopbackOptions,
            httpRequest,
            certificate,
            chain: null,
            SslPolicyErrors.RemoteCertificateChainErrors));
        Assert.False(IbkrGatewayTransport.ValidateLocalIbeamCertificate(
            nonIbeamOptions,
            loopbackRequest,
            certificate,
            chain: null,
            SslPolicyErrors.RemoteCertificateChainErrors));
    }

    [Fact]
    public void ValidateLocalIbeamCertificate_KeepsDefaultSuccessForValidCertificates()
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "https://gateway.paper.local/v1/api/iserver/auth/status");
        var options = CreateOptions("https://gateway.paper.local", IbkrGatewayContainerOptions.DefaultIbeamImage);

        Assert.True(IbkrGatewayTransport.ValidateLocalIbeamCertificate(
            options,
            request,
            certificate: null,
            chain: null,
            SslPolicyErrors.None));
    }

    private static IbkrGatewayOptions CreateOptions(string gatewayUrl, string image) => new()
    {
        GatewayBaseUrl = new Uri(gatewayUrl),
        GatewayContainer = new IbkrGatewayContainerOptions
        {
            Image = image,
            Port = 5000,
        },
    };

    private static X509Certificate2 CreateSelfSignedCertificate()
    {
        using var key = RSA.Create(2048);
        var request = new CertificateRequest("CN=127.0.0.1", key, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        return request.CreateSelfSigned(DateTimeOffset.UtcNow.AddDays(-1), DateTimeOffset.UtcNow.AddDays(1));
    }
}
