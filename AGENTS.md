# ATrade Agent Guidance

## Current Coordination Model

- The plan and the implementation work are in GitHub Issues and pull requests
  for `Mano-Liaoyan/ATrade`. There is no `PLAN.md`.
- `README.md` tells how to run and check ATrade.
- `docs/architecture.md` is the architecture specification. It is the
  implementation authority.
- `GLOSSARY.md` holds the terms.
- `docs/adr/` holds decisions that are hard to reverse, when they exist.

## Repo-Local Agent Skills

Reusable prompt skills are available under `.agents/skills/`. These are opt-in
skills for the current agent session.

- `skills-lock.json` records installed skill sources and hashes.
- Keep `.agents/skills/` and `skills-lock.json` in sync when adding, updating,
  or removing repo-local skills.

Current installed skills include:

- `setup-matt-pocock-skills` — configure issue-tracker, triage-label, and
  domain-doc context before using engineering or issue-workflow skills.
- `grill-with-docs` and `zoom-out` — domain/documentation-aware planning and
  codebase orientation.
- `diagnose`, `tdd`, and `improve-codebase-architecture` — bug investigation,
  test-first changes, and architecture refactoring support.
- `to-prd`, `to-issues`, and `triage` — PRD, issue, and triage workflow helpers.
- `caveman`, `grill-me`, and `write-a-skill` — productivity and skill-authoring
  helpers.
- `ste` (from `dualface/ste-zh`) and `asd-ste100` (from
  `danyuchn/asd-ste100-skill`) — ASD-STE100 writing rules for Chinese and
  English output.

`.claude/skills/ste` and `.claude/skills/asd-ste100` are relative symlinks to
`.agents/skills/` so Claude Code loads the same files. Other agents (Codex, pi)
read `.agents/skills/` directly. On Windows, clone with Developer Mode enabled
and `git config core.symlinks true`, or the links check out as plain text files.

## Writing Style

These rules are always on. They are not opt-in.

- Chinese writing and conversation: follow the `ste` skill.
- All other English writing and conversation: follow the `asd-ste100` skill.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for `Mano-Liaoyan/ATrade`. See `docs/agents/issue-tracker.md`.

### Triage labels

The default engineering-skill triage labels are used. See `docs/agents/triage-labels.md`.

### Domain docs

The domain docs are `GLOSSARY.md` and `docs/architecture.md`. ADRs go under `docs/adr/` when added. See `docs/agents/domain.md`.

## Startup Order For Coding Sessions

1. Read `README.md` for how to run and check ATrade.
2. Read the sections of `docs/architecture.md` that the task touches.
3. Read `GLOSSARY.md` for the terms.
4. Read the relevant GitHub issue or PR when one is supplied.

## Quality Gate

- `./scripts/check` runs all checks that CI runs. Run it before you finish a
  change. `./scripts/check backend`, `frontend`, and `e2e` run one part.
- Set `ATRADE_PLAYWRIGHT_PROJECTS` to the Playwright browsers that are
  installed, for example `"chromium firefox"`. CI runs all 4 projects.

## Frontend Design Rules

Apply these rules to every UI change in `frontend/`. The migration to Carbon
and Bits UI is issue #84. Before it is merged, apply the layout, copy, and
state rules to the current CSS.

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
- Do not add live order placement. `trading_mode=live` must stop the start.
- Frontend desktop browser behavior is a major product guardrail: latest stable Safari, Firefox, Chrome, and Edge must behave the same. When page scrolling is off, each region that can overflow (rails, panels, tables, lists) must have its own visible scroll track and thumb. No content can be clipped or unreachable. Safari can hide native scrollbars, so use styled tracks where reachability matters. Mobile layout is out of scope.
- Changes to HTTP or WebSocket interfaces, settings and `.env.example`, module boundaries, terms, or start and run commands must update the documents in the same change (`docs/architecture.md` section 18).
