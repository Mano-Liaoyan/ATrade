# The AI assistant saves strategy versions directly

The AI assistant saves each code change as a new strategy version through
`POST /api/strategies/{id}/versions`. It does not wait for the user to accept
the change. The reason is the loop "write code, check, backtest, change":
a backtest needs a saved strategy version, so an AI that can only propose code
cannot test its own change. The user keeps or discards each change in the
conversation. A discarded strategy version stays in the history with a mark,
because strategy versions do not change after they are saved and backtests
refer to them. Decided in
[#140](https://github.com/Mano-Liaoyan/ATrade/issues/140).

## Considered options

- The AI proposes code, and ATrade saves it only after the user keeps it.
  Rejected: the AI cannot backtest before each user click.
- The AI works in a separate copy of the strategy. Rejected: a comparison
  then crosses two strategies.

## Consequences

- Each strategy version records its source (user or AI assistant) and the
  conversation ID.
- The version list hides discarded strategy versions by default.
- Deleting a conversation never deletes a strategy version.
