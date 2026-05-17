---
status: active
owner: maintainer
updated: 2026-05-17
summary: Operations, Taskplane coordination, documentation authority, verification, and safety guardrail diagram for ATrade work.
see_also:
  - ../../INDEX.md
  - ../../tooling/taskplane-runtime-artifacts.md
  - ../overview.md
  - ../../process/github-coordination.md
  - ../../../AGENTS.md
  - ../../../tasks/CONTEXT.md
  - ../../../scripts/README.md
---

# Operations, Taskplane, And Safety

ATrade coordinates implementation through GitHub Issues and Taskplane packets,
while active docs remain the durable authority for architecture, runtime, and
safety decisions. Local runtime state and secrets stay outside committed files.

```mermaid
flowchart TD
    issue["GitHub issue or maintainer request"]
    packet["Taskplane packet<br/>PROMPT.md and STATUS.md"]
    scope["Packet dependencies and file scope"]
    agents["Pi runtime agents<br/>task-worker, task-reviewer, task-merger, supervisor"]
    done["Completed packet<br/>.DONE and archive when convenient"]

    subgraph authority["Documentation authority"]
        readme["README.md"]
        plan["PLAN.md"]
        context["tasks/CONTEXT.md"]
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

    issue --> packet
    packet --> scope
    scope --> agents
    agents --> done
    done --> plan
    done --> context

    readme --> plan
    plan --> context
    context --> index
    index --> activeDocs
    activeDocs --> diagrams
    packet -->|"must align with"| activeDocs

    start --> template
    start --> localEnv
    start --> compose
    start --> apphost
    localEnv -->|"secrets stay local"| secrets
    template -->|"safe defaults"| paper

    guardrails --> verification
    verification --> agents
    startTests --> start
    apphostTests --> compose
    apphostTests --> apphost
    frontendTests --> browser
    slnx --> activeDocs
```

```mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Packeted: create scoped Taskplane packet
    Packeted --> Blocked: explicit dependency open
    Blocked --> Packeted: dependency resolved
    Packeted --> Running: orchestrator dispatches work
    Running --> Review: implementation and verification ready
    Review --> Running: changes requested
    Review --> Merged: accepted and merged
    Merged --> Archived: .DONE marker and completed packet archive
    Archived --> [*]
```

## How To Read It

- `docs/INDEX.md` is the discovery layer. Only documents marked `active` are
  implementation authority.
- Taskplane file scope and dependency sections are the conflict-avoidance
  mechanism for orchestrated work. Local `.pi/` runtime state is not durable
  repository truth unless the tooling artifact doc explicitly lists it as
  committed project config.
- Verification is tied to the changed surface: solution-level .NET checks use
  `ATrade.slnx`, startup behavior uses the start-wrapper/AppHost/Compose tests,
  and frontend work keeps the route and desktop visibility guardrails.
- Safety rules cut across runtime and implementation: keep secrets local, keep
  committed defaults paper-only, reject live-trading paths, surface provider
  state honestly, and keep browser data access behind `ATrade.Api`.
