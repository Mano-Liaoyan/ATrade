# ATrade Agent Guidance

## Sources of Truth

- The plan and the implementation work are GitHub Issues and pull requests
  for `Mano-Liaoyan/ATrade`. See `docs/agents/issue-tracker.md` and
  `docs/agents/triage-labels.md`.
- `README.md` tells how to run and check ATrade.
- `docs/architecture.md` is the architecture specification. It is the
  implementation authority.
- `GLOSSARY.md` holds the terms. `docs/agents/domain.md` tells how to use
  the domain docs and ADRs (`docs/adr/`, when it exists).

## Startup Order For Coding Sessions

1. Read `README.md` for how to run and check ATrade.
2. Read the sections of `docs/architecture.md` that the task touches.
3. Read `GLOSSARY.md` for the terms.
4. Read the relevant GitHub issue or PR when one is supplied.

## Writing Style

These rules are always on.

- Chinese writing and conversation: follow the `ste` skill.
- All other English writing and conversation: follow the `asd-ste100` skill.

## Repo-Local Skills

The skills are in `.agents/skills/`. Codex and pi read them there. Each
`.claude/skills/<name>` is a relative symlink to `.agents/skills/<name>`, so
Claude Code loads the same files. On Windows, clone with Developer Mode
enabled and `git config core.symlinks true`, or the links check out as plain
text files.

When you add, update, or remove a skill, change `.agents/skills/`,
`.claude/skills/`, and `skills-lock.json` together.

## Quality Gate

- `./scripts/check` runs all checks that CI runs. Run it before you finish a
  change. `./scripts/check backend`, `frontend`, `assistant`, and `e2e` run
  one part.
- Set `ATRADE_PLAYWRIGHT_PROJECTS` to the Playwright browsers that are
  installed, for example `"chromium firefox"`. CI runs all 4 projects.

## Frontend Design Rules

Apply these rules to every UI change in `frontend/`.

- **Avoid unnecessary secondary labels and descriptions. Let the layout do
  the explaining.** This rule has the highest priority. A heading is a name
  only. Add a subtitle, a helper sentence, or a label above a heading only
  when it gives data that the user needs to act.
- Look: use the official Carbon v11 styles from `@carbon/styles`. Write the
  Carbon HTML structure and class names of the component. Write extra CSS
  only for parts that Carbon does not supply, and use only Carbon tokens,
  spacing, and type styles in it.
- Behavior: use Bits UI for selects, comboboxes, dialogs, tabs, menus,
  tooltips, and the command palette. Import `bits-ui` only in
  `src/lib/foundation/`.
- Themes: the user selects the theme with one icon button in the header. The
  icon shows the current selection: Light, Dark, or System (the default). A
  click changes to the next selection. Light uses Carbon g10, Dark uses g100,
  and System follows `prefers-color-scheme`. The header is a `cds--g100` zone
  in all themes.
- Type: IBM Plex Sans and IBM Plex Mono. Number columns use tabular numbers
  and right alignment.
- Surfaces: keep them flat. Use Carbon tiles, data tables, and dividers, one
  surface level deep. Color comes from Carbon tokens only.
- Copy: use the terms in `GLOSSARY.md`. A button says what it does, for
  example "Send paper order". A disabled control says why it is disabled.
- State: show a status with an icon or a word together with its color.

## Guardrails

- Keep the `./start run` contract: it runs `docker compose up` with
  `deploy/compose.yaml`. ATrade runs on Unix, and on Windows through WSL only.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR verification must use ignored local `.env` values and must skip cleanly when IB Gateway or `.env` is not available.
- Live order placement is not part of ATrade. `trading_mode=live` must stop the start.
- Frontend desktop browser behavior is a major product guardrail: latest stable Safari, Firefox, Chrome, and Edge must behave the same. When page scrolling is off, each region that can overflow (rails, panels, tables, lists) must have its own visible scroll track and thumb. All content must stay reachable. Safari can hide native scrollbars, so use styled tracks where reachability matters. Mobile layout is out of scope.
- Changes to HTTP or WebSocket interfaces, settings and `.env.example`, module boundaries, terms, or start and run commands must update the documents in the same change (`docs/architecture.md` section 18).
