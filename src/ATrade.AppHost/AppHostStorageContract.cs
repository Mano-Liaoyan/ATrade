namespace ATrade.AppHost;

public sealed record AppHostStorageContract(
    string PostgresDataVolumeName,
    string PostgresPassword,
    string TimescaleDataVolumeName,
    string TimescalePassword)
{
    public const string PostgresDataVolumeVariableName = "ATRADE_POSTGRES_DATA_VOLUME";
    public const string PostgresPasswordVariableName = "ATRADE_POSTGRES_PASSWORD";
    public const string TimescaleDataVolumeVariableName = "ATRADE_TIMESCALEDB_DATA_VOLUME";
    public const string TimescalePasswordVariableName = "ATRADE_TIMESCALEDB_PASSWORD";
    public const string DefaultPostgresDataVolumeName = "atrade-postgres-data";
    public const string DefaultPostgresPassword = "ATRADE_POSTGRES_PASSWORD";
    public const string DefaultTimescaleDataVolumeName = "atrade-timescaledb-data";
    public const string DefaultTimescalePassword = "ATRADE_TIMESCALEDB_PASSWORD";

    public static AppHostStorageContract Load(string contractPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(contractPath);

        var values = LoadMergedContractValues(contractPath);
        var postgresVolumeName = ResolveOptionalValue(values, PostgresDataVolumeVariableName) ?? DefaultPostgresDataVolumeName;
        var postgresPassword = ResolveOptionalValue(values, PostgresPasswordVariableName) ?? DefaultPostgresPassword;
        var timescaleVolumeName = ResolveOptionalValue(values, TimescaleDataVolumeVariableName) ?? DefaultTimescaleDataVolumeName;
        var timescalePassword = ResolveOptionalValue(values, TimescalePasswordVariableName) ?? DefaultTimescalePassword;

        return new AppHostStorageContract(
            NormalizeVolumeName(postgresVolumeName, PostgresDataVolumeVariableName, DefaultPostgresDataVolumeName),
            NormalizePassword(postgresPassword, DefaultPostgresPassword),
            NormalizeVolumeName(timescaleVolumeName, TimescaleDataVolumeVariableName, DefaultTimescaleDataVolumeName),
            NormalizePassword(timescalePassword, DefaultTimescalePassword));
    }

    private static string NormalizeVolumeName(string value, string variableName, string defaultValue)
    {
        var trimmed = value.Trim();
        if (string.IsNullOrWhiteSpace(trimmed))
        {
            return defaultValue;
        }

        if (!IsValidVolumeName(trimmed))
        {
            throw new InvalidOperationException(
                $"{variableName} must be a Docker-compatible named volume using letters, digits, '.', '_', or '-', and must start with a letter or digit; value was '{value}'.");
        }

        return trimmed;
    }

    private static string NormalizePassword(string value, string defaultValue)
    {
        var trimmed = value.Trim();
        if (string.IsNullOrWhiteSpace(trimmed))
        {
            return defaultValue;
        }

        return trimmed;
    }

    private static bool IsValidVolumeName(string value)
    {
        if (value.Length > 128 || !char.IsLetterOrDigit(value[0]))
        {
            return false;
        }

        foreach (var character in value)
        {
            if (!char.IsLetterOrDigit(character) && character is not '.' and not '_' and not '-')
            {
                return false;
            }
        }

        return true;
    }

    private static Dictionary<string, string> LoadMergedContractValues(string contractPath)
    {
        var contractDirectory = Path.GetDirectoryName(contractPath)
            ?? throw new InvalidOperationException($"Failed to resolve the local AppHost storage contract directory for '{contractPath}'.");
        var templatePath = Path.Combine(contractDirectory, ".env.template");
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        if (File.Exists(templatePath) &&
            !Path.GetFullPath(templatePath).Equals(Path.GetFullPath(contractPath), StringComparison.OrdinalIgnoreCase))
        {
            Overlay(values, ParseEnvironmentFile(templatePath));
        }

        Overlay(values, ParseEnvironmentFile(contractPath));
        return values;
    }

    private static void Overlay(IDictionary<string, string> destination, IReadOnlyDictionary<string, string> source)
    {
        foreach (var pair in source)
        {
            destination[pair.Key] = pair.Value;
        }
    }

    private static Dictionary<string, string> ParseEnvironmentFile(string path)
    {
        if (!File.Exists(path))
        {
            throw new InvalidOperationException($"Failed to load the local AppHost storage contract file at '{path}'.");
        }

        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var rawLine in File.ReadAllLines(path))
        {
            var line = rawLine.Trim();
            if (string.IsNullOrWhiteSpace(line) || line.StartsWith('#'))
            {
                continue;
            }

            var separatorIndex = line.IndexOf('=');
            if (separatorIndex <= 0)
            {
                continue;
            }

            var key = line[..separatorIndex].Trim();
            var value = line[(separatorIndex + 1)..].Trim().Trim('"', '\'');
            values[key] = value;
        }

        return values;
    }

    private static string? ResolveOptionalValue(IReadOnlyDictionary<string, string> values, string key)
    {
        var environmentValue = Environment.GetEnvironmentVariable(key);
        if (!string.IsNullOrWhiteSpace(environmentValue))
        {
            return environmentValue.Trim();
        }

        return values.TryGetValue(key, out var fileValue) && !string.IsNullOrWhiteSpace(fileValue)
            ? fileValue.Trim()
            : null;
    }
}
