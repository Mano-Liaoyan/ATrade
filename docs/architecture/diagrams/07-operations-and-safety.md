---
status: active
owner: maintainer
updated: 2026-05-21
summary: Operations, GitHub coordination, documentation authority, verification, and safety guardrail diagram for ATrade work.
see_also:
  - ../../INDEX.md
  - ../overview.md
  - ../../process/github-coordination.md
  - ../../../AGENTS.md
  - ../../../scripts/README.md
---

# Operations And Safety

ATrade coordinates implementation through GitHub Issues and pull requests, while
active docs remain the durable authority for architecture, runtime, and safety
decisions. Local runtime state and secrets stay outside committed files.

```mermaid
flowchart TD
    issue["GitHub issue or maintainer request"]
    branch["Local branch and code changes"]
    pr["Pull request"]

    subgraph authority["Documentation authority"]
        readme["README.md"]
        plan["PLAN.md"]
        index["docs/INDEX.md"]
        activeDocs["Active docs only"]
        diagrams["Architecture diagrams"]
    end

    subgraph runtime["Local runtime and secrets boundary"]
        start["start run contract<br/>Unix, PowerShell, Command Prompt"]
        template[".env.template committed defaults"]
        localEnv["ignored .env and process env"]
        compose["Compose infrastructure"]
        apphost["Aspire AppHost"]
    end

    subgraph verification["Verification net"]
        slnx["ATrade.slnx build and test"]
        startTests["start-wrapper tests"]
        apphostTests["AppHost and Compose contract tests"]
        frontendTests["frontend route, visibility, and workspace tests"]
    end

    subgraph guardrails["Safety guardrails"]
        secrets["No committed credentials, tokens, account ids, or cookies"]
        paper["Paper-only defaults"]
        noLive["No live order placement"]
        honest["Honest provider and cache states"]
        browser["Desktop scroll ownership and API-only browser access"]
    end

    issue --> branch
    branch --> pr
    pr --> plan

    readme --> plan
    plan --> index
    index --> activeDocs
    activeDocs --> diagrams
    branch -->|"must align with"| activeDocs

    start --> template
    start --> localEnv
    start --> compose
    start --> apphost
    localEnv -->|"secrets stay local"| secrets
    template -->|"safe defaults"| paper

    guardrails --> verification
    verification --> pr
    startTests --> start
    apphostTests --> compose
    apphostTests --> apphost
    frontendTests --> browser
    slnx --> activeDocs
```

```mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Ready: acceptance criteria clear
    Ready --> Running: implementation starts
    Running --> Review: implementation and verification ready
    Review --> Running: changes requested
    Review --> Merged: accepted and merged
    Merged --> [*]
```

## How To Read It

- `docs/INDEX.md` is the discovery layer. Only documents marked `active` are
  implementation authority.
- GitHub issues and PRs hold durable work state, acceptance criteria, blockers,
  and review discussion.
- Verification is tied to the changed surface: solution-level .NET checks use
  `ATrade.slnx`, startup behavior uses the start-wrapper/AppHost/Compose tests,
  and frontend work keeps the route and desktop visibility guardrails.
- Safety rules cut across runtime and implementation: keep secrets local, keep
  committed defaults paper-only, reject live-trading paths, surface provider
  state honestly, and keep browser data access behind `ATrade.Api`.
