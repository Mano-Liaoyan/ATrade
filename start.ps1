$ErrorActionPreference = 'Stop'

$Command = if ($args.Count -gt 0) { $args[0] } else { '' }
$Remaining = if ($args.Count -gt 1) { $args[1..($args.Count - 1)] } else { @() }

function Show-Usage {
    [Console]::Error.WriteLine('Usage: ./start.ps1 run')
}

switch ($Command) {
    'run' {
        & "$PSScriptRoot/scripts/start.run.ps1" @Remaining
        exit $LASTEXITCODE
    }
    '' {
        Show-Usage
        exit 1
    }
    default {
        [Console]::Error.WriteLine("Unsupported command: $Command")
        Show-Usage
        exit 1
    }
}
