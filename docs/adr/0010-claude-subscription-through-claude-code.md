# A Claude subscription runs through the official Claude Code binary

The AI assistant can use a Claude subscription only through the provider
`claude-code`: the Claude Agent SDK starts the official, unmodified `claude`
binary in the `assistant` container, and the binary uses its own Claude login.
The user logs in one time with `claude auth login` in the container. ATrade
never reads, stores, or sends that login, and the web page has no Claude
login. The reason: Anthropic permits a Claude subscription login only in
Claude Code and its own apps, and does not permit other apps to offer a Claude
login or to keep or send its tokens
([legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)).
pi's own `anthropic` subscription login sends the subscription token to the
Anthropic API outside Claude Code. It stays available (section 25.7.1 of
`docs/architecture/assistant.md`: the user takes the risk of the terms), but
the page shows its risk. Decided by the user on 2026-11-11.

## Considered options

- Remove pi's `anthropic` subscription login: the safest, but the user wants
  to keep it with a clear warning.
- A long-lived token from `claude setup-token` in `.env`: documented for
  scripts and CI, but the user selected the login in the container, which
  Claude Code refreshes itself and which never goes into a file of ATrade.
- A Claude login on the web page: not permitted by Anthropic.

## Consequences

- A conversation runs in pi or in Claude Code, and cannot change between
  them: the model context of each runner is in its own session.
- Each `claude` process uses about 200 to 250 MB, so the `assistant`
  container needs a higher memory limit (`2g`).
- The version of the `claude` binary is the version of the SDK package in
  `assistant/package.json`. The binary does not update itself.
- The Claude Code runs use the limits of the Claude subscription. ATrade is
  for one user, so this is the ordinary, individual use that Anthropic's
  limits assume.
