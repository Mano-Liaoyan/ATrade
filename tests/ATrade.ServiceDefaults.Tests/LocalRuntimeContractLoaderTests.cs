using ATrade.ServiceDefaults;

namespace ATrade.ServiceDefaults.Tests;

public sealed class LocalRuntimeContractLoaderTests
{
    [Fact]
    public void Load_applies_template_env_and_process_overlays_in_order()
    {
        using var repository = TemporaryRepository.Create();
        repository.WriteTemplate($$"""
{{LocalRuntimeEnvironmentVariables.ApiHttpPort}}=5181
{{LocalRuntimeEnvironmentVariables.PostgresDataVolume}}=template-postgres-volume
{{LocalRuntimeEnvironmentVariables.PostgresPassword}}=template-postgres-password
{{LocalRuntimeEnvironmentVariables.BrokerIntegrationEnabled}}=false
{{LocalRuntimeEnvironmentVariables.IbkrUsername}}=IBKR_USERNAME
{{LocalRuntimeEnvironmentVariables.IbkrPassword}}=IBKR_PASSWORD
{{LocalRuntimeEnvironmentVariables.FrontendApiBaseUrl}}=http://127.0.0.1:5181
{{LocalRuntimeEnvironmentVariables.NextPublicApiBaseUrl}}=http://127.0.0.1:5181
{{LocalRuntimeEnvironmentVariables.LeanWorkspaceRoot}}=template-lean-workspace
{{LocalRuntimeEnvironmentVariables.LeanContainerWorkspaceRoot}}=template-workspace
""");
        repository.WriteEnv($$"""
{{LocalRuntimeEnvironmentVariables.ApiHttpPort}}=6001
{{LocalRuntimeEnvironmentVariables.PostgresDataVolume}}=env-postgres-volume
{{LocalRuntimeEnvironmentVariables.IbkrUsername}}=env-paper-user
{{LocalRuntimeEnvironmentVariables.LeanWorkspaceRoot}}=env-lean-workspace
{{LocalRuntimeEnvironmentVariables.LeanContainerWorkspaceRoot}}=env-workspace
""");

        var contract = LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(
            RepositoryRoot: repository.Root,
            ContractPath: repository.EnvPath,
            EnvironmentVariables: new Dictionary<string, string?>
            {
                [LocalRuntimeEnvironmentVariables.ApiHttpPort] = "7001",
                [LocalRuntimeEnvironmentVariables.AspireDashboardHttpPort] = "7002",
                [LocalRuntimeEnvironmentVariables.PostgresPassword] = "process-postgres-password",
                [LocalRuntimeEnvironmentVariables.IbkrPassword] = "process-paper-password",
                [LocalRuntimeEnvironmentVariables.LeanWorkspaceRoot] = "process-lean-workspace",
                [LocalRuntimeEnvironmentVariables.LeanContainerWorkspaceRoot] = "process-workspace",
            }));

        Assert.Equal(Path.GetFullPath(repository.EnvPath), contract.LoadedFromPath);
        Assert.Equal(7001, contract.Ports.ApiHttpPort);
        Assert.Equal(7002, contract.Ports.AspireDashboardHttpPort);
        Assert.Equal(LocalRuntimeContractDefaults.FrontendDirectHttpPort, contract.Ports.FrontendDirectHttpPort);
        Assert.Equal("env-postgres-volume", contract.Storage.PostgresDataVolumeName);
        Assert.Equal("process-postgres-password", contract.Storage.PostgresPassword);
        Assert.Equal("false", contract.PaperTrading.BrokerIntegrationEnabled);
        Assert.Equal("env-paper-user", contract.PaperTrading.IbkrUsername);
        Assert.Equal("process-paper-password", contract.PaperTrading.IbkrPassword);
        Assert.Equal($"http://127.0.0.1:{contract.Ports.ApiHttpPort}", contract.Frontend.FrontendApiBaseUrl);
        Assert.Equal(contract.Frontend.FrontendApiBaseUrl, contract.Frontend.NextPublicApiBaseUrl);
        Assert.Equal(Path.Combine(repository.Root, "process-lean-workspace"), contract.Lean.WorkspaceRoot);
        Assert.Equal("/process-workspace", contract.Lean.ContainerWorkspaceRoot);
    }

    [Fact]
    public void Load_uses_safe_builtin_defaults_when_files_omit_known_values()
    {
        using var repository = TemporaryRepository.Create();
        repository.WriteTemplate("# intentionally empty to prove built-in safe defaults\n");

        var contract = LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(
            RepositoryRoot: repository.Root,
            ContractPath: repository.TemplatePath,
            EnvironmentVariables: new Dictionary<string, string?>()));

        Assert.Equal(LocalRuntimeContractDefaults.ApiHttpPort, contract.Ports.ApiHttpPort);
        Assert.Equal(LocalRuntimeContractDefaults.FrontendDirectHttpPort, contract.Ports.FrontendDirectHttpPort);
        Assert.Equal(LocalRuntimeContractDefaults.AppHostFrontendHttpPort, contract.Ports.AppHostFrontendHttpPort);
        Assert.Equal(LocalRuntimeContractDefaults.AspireDashboardHttpPort, contract.Ports.AspireDashboardHttpPort);
        Assert.Equal(LocalRuntimeContractDefaults.PostgresDataVolume, contract.Storage.PostgresDataVolumeName);
        Assert.Equal(LocalRuntimeContractDefaults.PostgresPassword, contract.Storage.PostgresPassword);
        Assert.Equal(LocalRuntimeContractDefaults.TimescaleDataVolume, contract.Storage.TimescaleDataVolumeName);
        Assert.Equal(LocalRuntimeContractDefaults.TimescalePassword, contract.Storage.TimescalePassword);
        Assert.Equal(LocalRuntimeContractDefaults.BrokerIntegrationEnabled, contract.PaperTrading.BrokerIntegrationEnabled);
        Assert.Equal(LocalRuntimeContractDefaults.BrokerAccountMode, contract.PaperTrading.BrokerAccountMode);
        Assert.Equal(LocalRuntimeContractDefaults.IbkrGatewayUrl, contract.PaperTrading.GatewayUrl);
        Assert.Equal(LocalRuntimeContractDefaults.IbkrGatewayPort, contract.PaperTrading.GatewayPort);
        Assert.Equal(LocalRuntimeContractDefaults.IbkrUsername, contract.PaperTrading.IbkrUsername);
        Assert.Equal(LocalRuntimeContractDefaults.IbkrPassword, contract.PaperTrading.IbkrPassword);
        Assert.Equal(LocalRuntimeContractDefaults.IbkrPaperAccountId, contract.PaperTrading.PaperAccountId);
        Assert.Equal(LocalRuntimeContractDefaults.MarketDataCacheFreshnessMinutes, contract.MarketData.CacheFreshnessMinutes);
        Assert.Equal(LocalRuntimeContractDefaults.AnalysisEngine, contract.Lean.AnalysisEngine);
        Assert.Equal(LocalRuntimeContractDefaults.LeanRuntimeMode, contract.Lean.RuntimeMode);
        Assert.Equal(Path.Combine(repository.Root, LocalRuntimeContractDefaults.LeanWorkspaceRoot), contract.Lean.WorkspaceRoot);
        Assert.Equal(LocalRuntimeContractDefaults.LeanContainerWorkspaceRoot, contract.Lean.ContainerWorkspaceRoot);
    }

    [Fact]
    public void Load_classifies_secret_and_non_secret_values()
    {
        using var repository = TemporaryRepository.Create();
        repository.WriteTemplate("# intentionally empty\n");

        var contract = LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(
            RepositoryRoot: repository.Root,
            ContractPath: repository.TemplatePath,
            EnvironmentVariables: new Dictionary<string, string?>()));

        AssertSecret(contract, LocalRuntimeEnvironmentVariables.PostgresPassword);
        AssertSecret(contract, LocalRuntimeEnvironmentVariables.TimescalePassword);
        AssertSecret(contract, LocalRuntimeEnvironmentVariables.IbkrUsername);
        AssertSecret(contract, LocalRuntimeEnvironmentVariables.IbkrPassword);
        AssertSecret(contract, LocalRuntimeEnvironmentVariables.IbkrPaperAccountId);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.ApiHttpPort);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.AspireDashboardHttpPort);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.PostgresDataVolume);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.IbkrGatewayUrl);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.IbkrGatewayImage);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.MarketDataCacheFreshnessMinutes);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.AnalysisEngine);
        AssertNonSecret(contract, LocalRuntimeEnvironmentVariables.LeanDockerImage);
    }

    [Theory]
    [InlineData(LocalRuntimeEnvironmentVariables.ApiHttpPort, "0")]
    [InlineData(LocalRuntimeEnvironmentVariables.FrontendDirectHttpPort, "70000")]
    [InlineData(LocalRuntimeEnvironmentVariables.AppHostFrontendHttpPort, "not-a-port")]
    [InlineData(LocalRuntimeEnvironmentVariables.AspireDashboardHttpPort, "70000")]
    public void Load_rejects_invalid_port_values(string variableName, string value)
    {
        using var repository = TemporaryRepository.Create();
        repository.WriteTemplate("# intentionally empty\n");

        var exception = Assert.Throws<InvalidOperationException>(() =>
            LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(
                RepositoryRoot: repository.Root,
                ContractPath: repository.TemplatePath,
                EnvironmentVariables: new Dictionary<string, string?>
                {
                    [variableName] = value,
                })));

        Assert.Contains(variableName, exception.Message, StringComparison.Ordinal);
        Assert.Contains(value, exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Load_rejects_invalid_docker_volume_names()
    {
        using var repository = TemporaryRepository.Create();
        repository.WriteTemplate("# intentionally empty\n");

        var exception = Assert.Throws<InvalidOperationException>(() =>
            LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(
                RepositoryRoot: repository.Root,
                ContractPath: repository.TemplatePath,
                EnvironmentVariables: new Dictionary<string, string?>
                {
                    [LocalRuntimeEnvironmentVariables.PostgresDataVolume] = "-bad-volume",
                })));

        Assert.Contains(LocalRuntimeEnvironmentVariables.PostgresDataVolume, exception.Message, StringComparison.Ordinal);
        Assert.Contains("-bad-volume", exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void LocalDevelopmentPortContract_maps_from_shared_runtime_contract()
    {
        using var repository = TemporaryRepository.Create();
        repository.WriteTemplate($$"""
{{LocalRuntimeEnvironmentVariables.ApiHttpPort}}=6201
{{LocalRuntimeEnvironmentVariables.FrontendDirectHttpPort}}=6202
{{LocalRuntimeEnvironmentVariables.AppHostFrontendHttpPort}}=6203
{{LocalRuntimeEnvironmentVariables.AspireDashboardHttpPort}}=0
""");
        var runtimeContract = LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(
            RepositoryRoot: repository.Root,
            ContractPath: repository.TemplatePath,
            EnvironmentVariables: new Dictionary<string, string?>()));

        var portContract = LocalDevelopmentPortContractLoader.FromRuntimeContract(runtimeContract);

        Assert.Equal(runtimeContract.RepositoryRoot, portContract.RepositoryRoot);
        Assert.Equal(runtimeContract.FrontendDirectory, portContract.FrontendDirectory);
        Assert.Equal(runtimeContract.LoadedFromPath, portContract.LoadedFromPath);
        Assert.Equal(runtimeContract.Ports.ApiHttpPort, portContract.ApiHttpPort);
        Assert.Equal(runtimeContract.Ports.FrontendDirectHttpPort, portContract.FrontendDirectHttpPort);
        Assert.Equal(runtimeContract.Ports.AppHostFrontendHttpPort, portContract.AppHostFrontendHttpPort);
        Assert.Equal(runtimeContract.Ports.AspireDashboardHttpPort, portContract.AspireDashboardHttpPort);
    }

    private static void AssertSecret(LocalRuntimeContract contract, string variableName)
    {
        Assert.True(contract.IsSecret(variableName), $"{variableName} should be classified as secret.");
        Assert.True(contract.Values[variableName].IsSecret);
    }

    private static void AssertNonSecret(LocalRuntimeContract contract, string variableName)
    {
        Assert.False(contract.IsSecret(variableName), $"{variableName} should be classified as non-secret.");
        Assert.False(contract.Values[variableName].IsSecret);
    }

    private sealed class TemporaryRepository : IDisposable
    {
        private TemporaryRepository(string root)
        {
            Root = root;
            TemplatePath = Path.Combine(root, ".env.template");
            EnvPath = Path.Combine(root, ".env");
        }

        public string Root { get; }

        public string TemplatePath { get; }

        public string EnvPath { get; }

        public static TemporaryRepository Create()
        {
            var root = Path.Combine(Path.GetTempPath(), $"atrade-runtime-contract-{Guid.NewGuid():N}");
            Directory.CreateDirectory(root);
            return new TemporaryRepository(root);
        }

        public void WriteTemplate(string content) => File.WriteAllText(TemplatePath, content);

        public void WriteEnv(string content) => File.WriteAllText(EnvPath, content);

        public void Dispose()
        {
            if (Directory.Exists(Root))
            {
                Directory.Delete(Root, recursive: true);
            }
        }
    }
}
