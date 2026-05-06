#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

assert_file_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi

  if ! grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_file_not_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ -f "$file_path" ]] && grep -Fqi -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_lean_provider_registration() {
  assert_file_contains "$repo_root/ATrade.slnx" 'ATrade.Analysis.Lean'
  assert_file_contains "$repo_root/ATrade.slnx" 'ATrade.Analysis.Lean.Tests'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/ATrade.Analysis.Lean.csproj" 'ATrade.Analysis.csproj'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" 'options.CliCommand'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" 'options.DockerCommand'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" '"exec"'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" 'MapHostPathToManagedContainerPath'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" 'LeanAnalysisEnvironmentVariables.ManagedContainerName'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" 'QuantConnect.Lean.Launcher.dll'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" 'lean-engine-config.json'
  assert_file_not_contains "$repo_root/src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs" '"run",'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAnalysisOptions.cs" 'quantconnect/lean:latest'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAnalysisOptions.cs" 'DefaultManagedContainerName'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAnalysisOptions.cs" 'ContainerWorkspaceRoot'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanInputConverter.cs" 'StrategyParameters'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAlgorithmTemplate.cs" 'self.strategy_id ='
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAlgorithmTemplate.cs" 'def _rsi_action'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAlgorithmTemplate.cs" 'def _breakout_action'
  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAnalysisResultParser.cs" 'ReadBacktestDetails'
  assert_file_contains "$repo_root/src/ATrade.Api/ATrade.Api.csproj" 'ATrade.Analysis.Lean.csproj'
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'AddLeanAnalysisEngine(builder.Configuration)'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'AddContainer("lean-engine"'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'LeanAnalysisRuntimeContract.Load'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'WithContainerName(leanRuntimeContract.ManagedContainerName)'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'WithBindMount(leanRuntimeContract.WorkspaceRoot, leanRuntimeContract.ContainerWorkspaceRoot, isReadOnly: false)'
  assert_file_contains "$repo_root/src/ATrade.AppHost/LeanAnalysisRuntimeContract.cs" 'ManagedContainerNameVariableName'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_ANALYSIS_ENGINE=none'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_LEAN_CLI_COMMAND=lean'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_LEAN_DOCKER_IMAGE=quantconnect/lean:latest'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_LEAN_TIMEOUT_SECONDS=45'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_LEAN_MANAGED_CONTAINER_NAME=atrade-lean-engine'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT=/workspace'
}

assert_provider_neutral_contracts() {
  if grep -RIn --exclude-dir=bin --exclude-dir=obj --exclude-dir=.git -E 'QuantConnect|ATrade\.Analysis\.Lean' "$repo_root/src/ATrade.Analysis" "$repo_root/frontend/types" "$repo_root/frontend/lib"; then
    printf 'core analysis and frontend contracts must remain provider-neutral.\n' >&2
    return 1
  fi

  assert_file_contains "$repo_root/frontend/types/analysis.ts" 'AnalysisEngineMetadata'
  assert_file_contains "$repo_root/frontend/types/analysis.ts" 'AnalysisResult'
  assert_file_contains "$repo_root/frontend/lib/analysisClient.ts" '/api/analysis/run'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx" 'data-testid="analysis-panel"'
  assert_file_contains "$repo_root/frontend/lib/terminalAnalysisWorkflow.ts" 'Analysis only — no brokerage routing or automatic order placement.'
  assert_file_not_contains "$repo_root/frontend/types/analysis.ts" 'QuantConnect'
}

assert_no_trading_side_effects() {
  if grep -RIn --exclude-dir=bin --exclude-dir=obj --exclude='LeanAnalysisGuardrails.cs' --exclude='LeanAnalysisEngineTests.cs' -E 'MarketOrder\(|LimitOrder\(|StopMarketOrder\(|StopLimitOrder\(|Liquidate\(|SetBrokerageModel|BrokerageName\.|SetLiveMode|IBrokerage|/api/orders' "$repo_root/src/ATrade.Analysis.Lean"; then
    printf 'LEAN analysis provider must not contain order-routing, brokerage, or live-trading calls.\n' >&2
    return 1
  fi

  assert_file_contains "$repo_root/src/ATrade.Analysis.Lean/LeanAnalysisGuardrails.cs" 'MarketOrder('
  assert_file_contains "$repo_root/tests/ATrade.Analysis.Lean.Tests/LeanAnalysisEngineTests.cs" 'AlgorithmTemplateStaysAnalysisOnlyAndRejectsTradingCalls'
}

assert_adapter_tests_and_runtime_skip() {
  dotnet test "$repo_root/tests/ATrade.Analysis.Lean.Tests/ATrade.Analysis.Lean.Tests.csproj" --nologo --verbosity minimal

  if command -v lean >/dev/null 2>&1; then
    if lean --version >/dev/null 2>&1; then
      printf 'LEAN CLI detected; adapter unit tests exercised the generated-workspace path with a deterministic runtime fixture.\n'
      return 0
    fi
  fi

  printf 'SKIP: official LEAN CLI is not installed or not executable; runtime execution is optional and adapter tests cover the LEAN workspace path and managed Docker command construction without requiring local LEAN/Docker credentials.\n'
}

main() {
  assert_lean_provider_registration
  assert_provider_neutral_contracts
  assert_no_trading_side_effects
  assert_adapter_tests_and_runtime_skip
}

main "$@"
