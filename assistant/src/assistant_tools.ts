// The tool list of the AI assistant (docs/architecture/assistant.md 25.4.1). pi may run only these tools.
// Phase 3 adds the screen tools of 25.4.3.
export const ASSISTANT_TOOL_NAMES: readonly string[] = [
  'list_strategies',
  'read_strategy',
  'read_strategy_version',
  'create_strategy',
  'save_strategy_version',
  'run_backtest',
  'list_backtests',
  'read_backtest',
  'compare_backtests',
];
