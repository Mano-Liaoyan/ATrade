namespace ATrade.Brokers.Ibkr;

public sealed class IbkrGatewayContainerOptions
{
    public const string DefaultIbeamImage = "voyz/ibeam:latest";
    public const string IbeamAccountEnvironmentVariable = IbkrGatewayEnvironmentVariables.IbeamAccount;
    public const string IbeamPasswordEnvironmentVariable = IbkrGatewayEnvironmentVariables.IbeamPassword;

    public string? Image { get; set; }

    public int? Port { get; set; } = 5000;

    public bool IsIbeamImage => string.Equals(Image, DefaultIbeamImage, StringComparison.OrdinalIgnoreCase);
}
