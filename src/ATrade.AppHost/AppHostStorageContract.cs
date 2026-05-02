using ATrade.ServiceDefaults;

namespace ATrade.AppHost;

public sealed record AppHostStorageContract(
    string PostgresDataVolumeName,
    string PostgresPassword,
    string TimescaleDataVolumeName,
    string TimescalePassword)
{
    public const string PostgresDataVolumeVariableName = LocalRuntimeEnvironmentVariables.PostgresDataVolume;
    public const string PostgresPasswordVariableName = LocalRuntimeEnvironmentVariables.PostgresPassword;
    public const string TimescaleDataVolumeVariableName = LocalRuntimeEnvironmentVariables.TimescaleDataVolume;
    public const string TimescalePasswordVariableName = LocalRuntimeEnvironmentVariables.TimescalePassword;
    public const string DefaultPostgresDataVolumeName = LocalRuntimeContractDefaults.PostgresDataVolume;
    public const string DefaultPostgresPassword = LocalRuntimeContractDefaults.PostgresPassword;
    public const string DefaultTimescaleDataVolumeName = LocalRuntimeContractDefaults.TimescaleDataVolume;
    public const string DefaultTimescalePassword = LocalRuntimeContractDefaults.TimescalePassword;

    public static AppHostStorageContract Load(string contractPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(contractPath);

        return Load(LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(ContractPath: contractPath)));
    }

    public static AppHostStorageContract Load(LocalRuntimeContract runtimeContract)
    {
        ArgumentNullException.ThrowIfNull(runtimeContract);

        return new AppHostStorageContract(
            runtimeContract.Storage.PostgresDataVolumeName,
            runtimeContract.Storage.PostgresPassword,
            runtimeContract.Storage.TimescaleDataVolumeName,
            runtimeContract.Storage.TimescalePassword);
    }
}
