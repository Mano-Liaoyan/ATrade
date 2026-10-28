# Research: how to connect pi to ATrade

Ticket: [#133 pi 接入方式](https://github.com/Mano-Liaoyan/ATrade/issues/133).
Map: [#129](https://github.com/Mano-Liaoyan/ATrade/issues/129).
Date: 2026-10-28.

## Status of the facts

Each fact has one of these marks:

- **[docs]**: read in the pi documentation at commit `edab3ef` of
  `github.com/badlogic/pi-mono` (now `github.com/earendil-works/pi`), path
  `packages/coding-agent/docs/`.
- **[source]**: read in the pi source code at the same commit.
- **[run]**: run-verified with `@earendil-works/pi-coding-agent@1.4.0` from
  npm, on Node 24.15.0, in a scratch folder. No account login was used. A fake
  OpenAI-compatible model server on `127.0.0.1` gave the model replies.
- **[vendor]**: read on a vendor page (link given). Vendor terms change
  often. Read them again before the implementation.

## Summary

1. Run pi in a new Compose service, `assistant`. It is a small Node process.
   The `web` service relays the conversation to the browser over a WebSocket.
   Do not run pi inside `web`. `web` holds the database URL and the IBKR
   settings, and pi must not see them.
2. Use the pi SDK (in-process TypeScript) in the `assistant` service. RPC
   mode also works and was run-verified. The SDK gives full control of
   tools, sessions, resources, and credentials in one process.
3. Give pi only custom tools. Turn off all built-in tools (`bash`, `edit`,
   `write`, and the others). Strategy code goes to ATrade as a tool argument,
   so pi does not need to write files.
4. ATrade itself must enforce what the AI can do. Give the `assistant`
   service a separate listener with an allow list of routes. Paper order and
   forward test routes must not be on it. Do not trust tool restrictions in
   pi alone, because pi extensions run with full process permissions.
5. Subscription risk, from low to high: OpenAI "ChatGPT subscription"
   (Sign in with ChatGPT for open-source apps), GitHub Copilot, OpenAI
   Codex login, Anthropic Claude Pro/Max login. For Anthropic, use an API key.
   pi 1.4.0 has no Google Gemini subscription login. Gemini works only with
   an API key.
6. pi is MIT licensed.

## 1. The package

- The npm package is now `@earendil-works/pi-coding-agent` (version 1.4.0,
  MIT, Node `>=22.19.0`). [run: `npm view`]
- The old package `@mariozechner/pi-coding-agent` stops at 0.73.1. npm marks
  it deprecated with the text "please use @earendil-works/pi-coding-agent
  instead going forward". [run: `npm view`]
- The repository moved to `github.com/earendil-works/pi`. The old URL
  `github.com/badlogic/pi-mono` still clones. [docs: `README.md`]
- License: MIT, copyright Mario Zechner. [source: `LICENSE`] ATrade can
  bundle and change it. Keep the license text in the image.

## 2. Embedding options

pi has 4 interfaces. [docs: `README.md`, `rpc.md`, `sdk.md`, `cli.md`]

| Interface | How it runs | Fit for ATrade |
|---|---|---|
| Interactive TUI | Terminal UI | No. Use it only to log in (section 4). |
| Print and JSON mode (`pi -p`, `--mode json`) | One prompt, then exit | No. One run per process, no multi-turn control. |
| RPC mode (`pi --mode rpc`) | Long-lived child process, JSONL on stdin and stdout | Yes. Any language can drive it. |
| SDK (`createAgentSession()`) | In a Node or Bun process | Yes. Full API. |

### 2.1 RPC mode

- Commands go to stdin as one JSON object per line. Responses and session
  events come from stdout. Each command can have an `id`. The response
  repeats it. [docs: `rpc.md`] [run]
- Commands include `prompt`, `steer`, `follow_up`, `abort`, `new_session`,
  `get_state`, `get_messages`, `set_model`, `compact`, `switch_session`,
  `fork`, `get_entries`, and `get_tree`. [docs: `rpc-commands.md`]
- There is no RPC command to log in. [docs: `rpc-commands.md`] [source:
  `src/modes/rpc/`]
- A `prompt` response only says that pi accepted the prompt
  (`"disposition": "started"`). The run continues as events. Wait for
  `agent_settled`. [docs: `rpc.md`] [run]
- Split stdout only on LF. Node `readline` also splits on U+2028 and U+2029,
  which is wrong for this protocol. The pi docs give a Python client that
  reads binary lines. [docs: `rpc.md`]
- Close stdin to stop pi. [docs: `rpc.md`] [run]

Run-verified event order for one prompt that calls one custom tool [run]:

```
response(prompt, disposition=started)
agent_start
turn_start
message_start / message_end           (role: system)
message_start / message_end           (role: user)
message_start                         (role: assistant, stopReason: pending)
message_update  text_start / text_delta / text_end
message_update  toolcall_start / toolcall_delta / toolcall_end
message_end                           (role: assistant, with toolCall blocks)
tool_execution_start                  (toolCallId, toolName, args)
tool_execution_end                    (result.content, result.details, isError)
message_start / message_end           (role: toolResult)
turn_end
turn_start ... (second model call with the tool result) ... turn_end
agent_end
agent_settled                         (aborted: false)
```

Other run-verified shapes [run]:

- Bad JSON on stdin gives
  `{"type":"response","command":"parse","success":false,"error":"Failed to parse command: ..."}`
  with no `id`.
- A `prompt` with no credential gives `success: false` and the error
  "No API key found for the selected model."
- `get_state` gives the model, `thinkingLevel`, `isStreaming`, `sessionId`,
  `sessionFile`, and `messageCount`.

### 2.2 SDK

- `createAgentSession()` gives an `AgentSession`. `session.subscribe()` gives
  the same events as RPC mode. `session.prompt()` resolves when the run
  ends. [docs: `sdk.md`]
- The host can supply each part: `modelRuntime` (credentials and models),
  `settingsManager`, `sessionManager`, `resourceLoader` (extensions, skills,
  context files), `tools`, `noTools`, `excludeTools`, and `customTools`.
  [docs: `sdk.md`]
- `AgentSessionRuntime` gives `newSession()`, `switchSession()`, and
  `fork()`. [docs: `sdk.md`]
- `ModelRuntime.create({ authPath, modelsPath })` puts `auth.json` and
  `models.json` in a path that the host selects. [source:
  `examples/sdk/09-api-keys-and-oauth.ts`]

### 2.3 Which fits a Python backend and a browser UI

The backend is Python. pi needs Node 22.19 or newer. So pi runs in its own
process in all options.

| Option | Description | Good | Bad |
|---|---|---|---|
| A. RPC child of `web` | `web` starts `pi --mode rpc` | No Node server to write | Node goes into the `web` image. pi gets the environment of `web` (database URL, IBKR settings). One child process for each conversation. |
| B. `assistant` service with RPC | A Node or Python bridge in a new container starts `pi --mode rpc` | Process isolation | Two protocols (bridge to pi, `web` to bridge). |
| C. `assistant` service with the SDK | A small Node server in a new container uses the SDK. `web` relays to it. | One process for all sessions. Full control of tools, resources, and credentials. No secrets of `web` in it. | ATrade gets a second language in the backend. |

Recommendation: option C. Option B is the fall-back when the user does not
want TypeScript code in ATrade. Option A is not safe enough.

## 3. Stream the conversation to the browser

- pi emits deltas: `message_update` with `text_delta`, `thinking_delta`, and
  `toolcall_delta`. `message_end` holds the final message. [docs: `json.md`]
  [run]
- On the RPC wire, `message_update` holds only the delta, not the full
  message. [docs: `json.md`]
- Proposed path: browser ⇄ `web` at a new `/ws/assistant` route ⇄
  `assistant` service. This keeps one published port and Cloudflare Access
  in front, as in `docs/architecture.md` section 14. `web` sends the pi
  events to the browser with no change, or maps them to a smaller ATrade
  message set.
- The browser sends `prompt`, `steer` (a new message while the run
  continues), and `abort`. [docs: `rpc-commands.md`]
- Extension dialogs (`select`, `confirm`, `input`) become
  `extension_ui_request` records in RPC mode. The client answers with
  `extension_ui_response`. [docs: `rpc-extension-ui.md`] ATrade can use this
  path to ask the user before a long backtest. This is an option, not a
  requirement.

## 4. Subscription logins and credentials

### 4.1 Logins that pi 1.4.0 supports

The OAuth flows in pi 1.4.0 are [source: `packages/ai/src/auth/oauth/*.ts`]:

| pi name | Provider | Headless method |
|---|---|---|
| Anthropic (Claude Pro/Max) | `anthropic` | "Copy code login (headless)": paste the code or the redirect URL |
| OpenAI (ChatGPT Plus/Pro) | `openai-codex` | "Device code login (headless)" |
| OpenAI (ChatGPT subscription) | `openai-chatgpt` | Local callback on port 1455. `PI_OAUTH_CALLBACK_HOST` changes the host. |
| GitHub Copilot | `github-copilot` | GitHub device code |
| xAI (Grok/X subscription) | `xai` | not checked |
| Kimi Code (subscription) | `kimi-coding` | not checked |
| Meta (Muse subscription) | `meta` | not checked |
| OpenRouter OAuth | `openrouter` | not checked |
| Radius | `radius` | not checked |

- pi removed the Google Gemini CLI and Google Antigravity logins. [docs:
  `CHANGELOG.md`] Google Gemini works only with `GEMINI_API_KEY`. [docs:
  `providers.md`]
- On a remote machine, the OAuth callback may not reach pi. pi then asks for
  the redirect URL or the code. [docs: `providers.md`]

### 4.2 Where pi keeps credentials

- `/login` writes the credential to `<agent-dir>/auth.json`. The default
  agent folder is `~/.pi/agent`. `PI_CODING_AGENT_DIR` changes it. [docs:
  `configuration.md`]
- pi writes `auth.json` with mode `0600` and its folder with mode `0700`. It
  uses a file lock for token refresh. [source: `src/core/auth-storage.ts`]
  [run: mode `600` seen]
- Credential order: `--api-key`, then `auth.json`, then `models.json`, then
  environment variables. [docs: `models.md`]
- An `auth.json` key can be a command that starts with `!`. pi runs it and
  keeps the result in memory only. [docs: `providers.md`]
- `pi auth check --provider <p>` prints `ready`, `not_ready`, or `invalid`.
  [docs: `cli.md`]

### 4.3 Login on the headless server in a container

There is no login command in RPC mode. Proposed procedure:

1. Mount a named volume (for example `atrade-assistant-pi`) on the agent
   folder of the `assistant` service.
2. The user runs
   `docker compose exec -it assistant pi` once and types `/login`.
3. The user selects a headless method (device code or copy code) and
   completes it in the browser on another device.
4. pi writes `auth.json` to the volume. The `assistant` service reads it and
   refreshes the tokens.

For an API key, put it in `.env` (ignored by git) and pass it as the
provider variable, for example `ANTHROPIC_API_KEY`. This follows the
guardrail in `AGENTS.md`: keep secrets out of git.

## 5. Terms of service risk

Use: one person, own subscription, own self-hosted server, pi as the client.
This is not legal advice. The vendor text is quoted or summarized from the
links.

| Subscription | What the vendor says | What pi does | Risk |
|---|---|---|---|
| Anthropic Claude Pro/Max | OAuth is "designed to support ordinary use of Claude Code and other native Anthropic applications". Developers must use API keys. [vendor: [Claude Code legal](https://code.claude.com/docs/en/legal-and-compliance)] Tools that "misrepresent their identity to Anthropic's servers" are prohibited. Anthropic can bill third-party tools to usage credits, not plan limits. [vendor: [Log in to your Claude account](https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account)] | With OAuth, pi sends Claude Code identity headers (`user-agent: claude-cli/...`, `x-app: cli`) and the system prompt line "You are Claude Code". [source: `packages/ai/src/api/anthropic-messages.ts`] pi itself shows a warning: "Third-party harness usage draws from extra usage and is billed per token, not your Claude plan limits." [source: `interactive-mode.ts`] | **High.** The identity headers match the prohibited case. Use an Anthropic API key. Max plans now include monthly API credits for API-key use. [vendor: [Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)] |
| OpenAI ChatGPT (`openai-chatgpt`) | Sign in with ChatGPT has a flow for "open-source and locally hosted apps". Paid or remotely hosted apps must complete an interest form. The token gives "eligible Responses API requests" only. [vendor: [SIWC for open source](https://developers.openai.com/siwc/token-sharing-open-source)] | pi registers a user-defined agent (`dynamic_agent_client`, name hint "Pi") and asks for scope `chatgpt.tokens.use.direct`. [source: `auth/oauth/openai-chatgpt.ts`] | **Low.** This is the vendor's own flow for open-source clients. Open item: ATrade runs on a remote server for one user. Check whether OpenAI counts this as "remotely hosted". Plan eligibility is on a "Preview limitations" page that was not read. |
| OpenAI Codex (`openai-codex`) | Codex docs cover only the Codex clients. Access tokens are "intended for trusted scripts, schedulers, and private CI runners". [vendor: [Codex auth](https://learn.chatgpt.com/docs/auth)] | pi uses the Codex login and the Codex backend. [source: `auth/oauth/openai-codex.ts`] | **Medium.** Not prohibited in the text read. Not permitted in the text read. Prefer `openai-chatgpt`. |
| GitHub Copilot | GitHub supports Copilot subscriptions in OpenCode through a partnership. [vendor: [GitHub changelog 2026-01-16](https://github.blog/changelog/2026-01-16-github-copilot-now-supports-opencode/)] No GitHub text that names pi was found. | pi sends VS Code Copilot Chat headers (`Editor-Version: vscode/...`, `Copilot-Integration-Id: vscode-chat`) and the VS Code client ID. [source: `auth/oauth/github-copilot.ts`] | **Medium.** pi presents itself as VS Code. |
| Google Gemini | Not researched. | No subscription login in pi 1.4.0. | Not applicable. Use an API key. |
| xAI, Kimi, Meta | Not researched. | Login exists. | Unknown. |

API keys of all vendors have no such risk. They cost money for each token.

## 6. Custom tools that call ATrade

- An extension registers a tool with `pi.registerTool({ name, description,
  parameters, execute })`. `parameters` is a TypeBox schema. `execute`
  returns `content` (to the model) and `details` (to the UI and the
  session). [docs: `extensions.md` "Custom Tools"] [run]
- The SDK can also pass tools directly with `customTools`. [docs: `sdk.md`]
- A tool can stream progress with `onUpdate`. [docs: `extensions.md`]
  A backtest tool can use it to send the queue state.

Proposed tools. Each calls one existing ATrade route.

| Tool | Route | Source |
|---|---|---|
| `list_strategies` | `GET /api/strategies` | `docs/architecture/strategy.md` |
| `read_strategy_version` | `GET /api/strategies/{id}/versions/{n}` | same |
| `create_strategy` | `POST /api/strategies` | same |
| `save_strategy_version` | `POST /api/strategies/{id}/versions` (body `{"code"}`. A `422` gives `problems` with line numbers. Return them to the model.) | same |
| `run_backtest` | `POST /api/backtests` | `docs/architecture/backtest.md` |
| `list_backtests` | `GET /api/backtests` | same |
| `read_backtest` | `GET /api/backtests/{id}` (metrics, equity curve, trades) | same |
| `compare_backtests` | `GET /api/backtests/{id}/comparison/{other}` | same |

`read_backtest` must wait or poll, because `POST /api/backtests` only queues
the backtest. A summary of the equity curve and the trades is better than the
full arrays, because the full arrays use many tokens.

## 7. Restrict commands and file writes

### 7.1 What pi gives

- The default tools are `read`, `bash`, `edit`, and `write`. [docs: `cli.md`]
- `--no-builtin-tools` removes all built-in tools and keeps extension tools.
  `--tools a,b` is an allow list. `--exclude-tools` removes tools. `--no-tools`
  removes all tools. The SDK has the same options. [docs: `cli.md`, `sdk.md`]
- With `--no-builtin-tools`, the model only receives the custom tools. A call
  to `bash` gives the result "Tool bash not found" with `isError: true`.
  [run]
- A `tool_call` event handler can block any call with `{ block: true,
  reason }`. [docs: `extensions.md`] The test used `--tools run_backtest,bash`
  and a handler that blocks all tools except `run_backtest`. The `bash` call
  gave the result "tool bash is not allowed". [run]
- An extension can replace a built-in tool by name (for example a `read`
  that accepts only one folder). [docs: `extensions.md`]
- pi has no built-in sandbox. The docs say: treat model commands as
  untrusted, and use a container for real isolation. [docs: `security.md`,
  `containerization.md`]
- `--no-approve` stops loading of project `.pi` resources and project
  `.agents/skills` in RPC mode. [docs: `security.md`]
- `--no-context-files` stops loading of `AGENTS.md` and `CLAUDE.md`. These
  files load without project trust. [docs: `security.md`, `cli.md`]
- Skills in `~/.agents/skills/` loaded although the agent folder was a
  scratch folder. [run: `get_commands` listed a user skill] In the container,
  keep `HOME` empty of skills, or use `--no-skills`, or give a custom
  `resourceLoader` in the SDK.

### 7.2 Proposed controls

1. Built-in tools: off. Strategy code goes in the `save_strategy_version`
   argument. If pi must read skills, add a `read` tool that accepts only the
   skills folder.
2. Container: read-only root file system, no ATrade secrets in the
   environment, only the volume for `auth.json` and sessions.
3. Network: the `assistant` service reaches only the ATrade assistant
   listener and the model providers. It does not reach `ib-gateway` or
   `postgres`.
4. ATrade side: `web` gives the `assistant` service a separate listener (or
   port) with an allow list of the routes in section 6. Paper order routes,
   forward test routes, and `PUT /api/backtest-limits` are not on it. Today
   `web` has no authentication of its own (Cloudflare Access is at the edge,
   `docs/architecture.md` section 14). So a pi process that reaches the main
   port can call all routes. The separate listener closes this hole.
5. pi `tool_call` handler: block all tool names that are not on the list.
   This is a second line, not the main control.

### 7.3 Extensions that pi writes

The user wants pi to write its own extensions. An extension runs in the pi
process with full permissions. [docs: `extensions.md` "Extension
Locations"] An extension can register any tool and can call any network
address that the container reaches. So an extension can go around controls
1 and 5. Controls 2, 3, and 4 still apply.

Proposed rule:

1. pi writes a new extension as text (a tool result or a file in a staging
   folder), not into a folder that pi loads.
2. The user reads it in the ATrade UI and accepts it.
3. ATrade copies it to the extensions folder. The `assistant` service loads
   it at the next session start (`ctx.reload()` or a new session). [docs:
   `extensions.md` `ctx.reload()`]

This makes the "write own extensions" feature a code review step, the same
as a strategy version. It needs a design decision on the map.

## 8. Session persistence

- pi saves each session as one JSONL file. The entries form a tree
  (`id`, `parentId`), so branches stay in one file. [docs:
  `session-format.md`]
- Default folder: `~/.pi/agent/sessions/--<path>--/`. `--session-dir` or
  `PI_CODING_AGENT_SESSION_DIR` changes it. With `--session-dir`, the files
  went directly into that folder, named `<timestamp>_<session-id>.jsonl`.
  [docs: `sessions.md`] [run]
- `--no-session` or `SessionManager.inMemory()` keeps nothing. [docs:
  `sessions.md`, `sdk.md`]
- pi compacts old history when the context is near the model limit. The
  file keeps the original entries. [docs: `sessions.md`]

Options for ATrade:

| Option | Description |
|---|---|
| pi files in a volume | Simple. The list of conversations comes from pi (`get_tree`, `switch_session`). Backups of PostgreSQL do not include them. |
| PostgreSQL | ATrade keeps the messages in its own table and gives them to the SDK `SessionManager`. More work. One backup. |

The map lists "conversation storage" under "Not yet specified". This
research does not decide it.

## 9. Other facts that affect the design

- The default system prompt says "You are an expert coding assistant
  operating inside pi". [run] Replace it with `SYSTEM.md` or the SDK.
  [docs: `configuration.md`]
- pi sends install telemetry and provider attribution headers.
  `PI_TELEMETRY=0` turns them off. `PI_OFFLINE=1` stops catalog refresh.
  [docs: `environment-variables.md`]
- A session file can contain all tool arguments and results. [docs:
  `security.md`] Treat the volume as private data.

## 10. Open items

1. The user decides option B or C (section 2.3).
2. The user decides which subscription or API key to use (section 5).
3. Check the OpenAI "Preview limitations" page and the "remotely hosted"
   rule for Sign in with ChatGPT.
4. The design of the assistant listener in `web` (section 7.2, control 4).
5. The review flow for extensions that pi writes (section 7.3).
6. Conversation storage (section 8).

## Sources

- pi repository, commit `edab3ef`: <https://github.com/earendil-works/pi>
  (`packages/coding-agent/docs/rpc.md`, `rpc-commands.md`, `json.md`,
  `rpc-extension-ui.md`, `sdk.md`, `extensions.md`, `cli.md`, `providers.md`,
  `models.md`, `configuration.md`, `security.md`, `containerization.md`,
  `sessions.md`, `session-format.md`, `skills.md`,
  `environment-variables.md`, `CHANGELOG.md`, and `packages/ai/src/auth/`)
- npm: <https://www.npmjs.com/package/@earendil-works/pi-coding-agent>
- Anthropic: <https://code.claude.com/docs/en/legal-and-compliance>,
  <https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account>,
  <https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan>
- OpenAI: <https://developers.openai.com/siwc/token-sharing-open-source>,
  <https://learn.chatgpt.com/docs/auth>
- GitHub: <https://github.blog/changelog/2026-01-16-github-copilot-now-supports-opencode/>
