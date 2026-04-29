# Task: TP-005 — Establish GitHub coordination primitives

**Created:** 2026-04-23
**Size:** M

## Review Level: 1 (Light)

**Assessment:** Adds durable coordination artifacts (`.github` templates, label
manifest, and an active process doc) that shape how autonomous work is queued,
claimed, blocked, resumed, and reviewed. No product code or runtime behavior
changes.
**Score:** 3/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-005-github-coordination-primitives/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Create the first durable GitHub coordination primitives for the ATrade agent
workforce so issues and PRs can carry workflow state outside chat history.

This task should codify the recommended label taxonomy from `AGENTS.md`, define
issue sizing and blocked-work resume rules from the Scrum Master plan, and add
repo-local templates that make those rules easy to follow.

## Scope

Deliver the minimum reusable coordination kit:

1. A repo-local label manifest that captures the desired workflow and role labels.
2. GitHub issue template(s) for implementation and coordination/governance work.
3. A pull request template that requires linked issue, docs, and verification context.
4. An active process doc that explains label meaning, sizing rules, and blocked/resume flow.

This task defines the **repository-side contract**. It does not need to mutate
live labels on the remote.

## Dependencies

- **None**

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `.pi/skills/github-coordination/SKILL.md`
- `plans/scrum-master/CURRENT.md`

## Environment

- **Workspace:** Project root
- **Services required:** None

## File Scope

- `.github/labels.yml` (new)
- `.github/ISSUE_TEMPLATE/config.yml` (new)
- `.github/ISSUE_TEMPLATE/implementation.yml` (new)
- `.github/ISSUE_TEMPLATE/coordination.yml` (new)
- `.github/PULL_REQUEST_TEMPLATE.md` (new)
- `docs/process/github-coordination.md` (new)
- `docs/INDEX.md`
- `README.md` (if a pointer to the coordination doc is warranted)
- `plans/scrum-master/CURRENT.md` (if affected)

## Steps

### Step 0: Preflight

- [ ] Read `AGENTS.md`, the GitHub coordination skill, and the Scrum Master plan
- [ ] Confirm `.github/` does not yet contain coordination templates or a label manifest
- [ ] Extract the recommended workflow and role labels from the active docs

### Step 1: Define the label manifest

- [ ] Create `.github/labels.yml`
- [ ] Include the recommended workflow labels from `AGENTS.md`
- [ ] Include the recommended role labels from `AGENTS.md`
- [ ] Record name, description, and color for each label

### Step 2: Add GitHub templates

- [ ] Create `.github/ISSUE_TEMPLATE/config.yml`
- [ ] Create `.github/ISSUE_TEMPLATE/implementation.yml`
- [ ] Create `.github/ISSUE_TEMPLATE/coordination.yml`
- [ ] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] Ensure the templates capture issue size, owning role, docs impact, verification, and unblock notes where relevant

### Step 3: Add the coordination doc

- [ ] Create `docs/process/github-coordination.md` with required frontmatter
- [ ] Document workflow-state labels and role labels
- [ ] Define issue sizing rules that align with Taskplane sizing (`S`, `M`, `L`, `XL`)
- [ ] Define how blocked work moves to `agent:needs-human`, then back to `agent:resume-ready`
- [ ] Cross-link `AGENTS.md`, `PLAN.md`, and the GitHub templates/manifest

### Step 4: Update the doc index and pointers

- [ ] Add the new coordination doc to `docs/INDEX.md`
- [ ] Update `README.md` only if a human-facing pointer to the new coordination contract is needed

### Step 5: Verification

- [ ] `rg -n "agent:ready|agent:blocked|agent:resume-ready|role:architect|role:senior-engineer" .github/labels.yml docs/process/github-coordination.md .github/ISSUE_TEMPLATE .github/PULL_REQUEST_TEMPLATE.md`
- [ ] Confirm every label referenced in the templates or process doc exists in `.github/labels.yml`
- [ ] Confirm `docs/INDEX.md` lists `docs/process/github-coordination.md`

### Step 6: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `docs/INDEX.md`
**Check If Affected:** `README.md`, `plans/scrum-master/CURRENT.md`

## Completion Criteria

- [ ] A durable label manifest exists in the repo
- [ ] Issue and PR templates exist for the intended coordination flow
- [ ] An active coordination doc defines sizing and blocked/resume behavior
- [ ] `docs/INDEX.md` lists the coordination doc

## Git Commit Convention

- **Implementation:** `docs(TP-005): description`
- **Checkpoints:** `checkpoint: TP-005 description`

## Do NOT

- Attempt to push labels directly to the remote from this task
- Add GitHub Actions automation in this slice
- Invent labels that conflict with the active `AGENTS.md` recommendations without updating the authoritative docs
- Treat PR state alone as the scheduler; the templates and doc must reinforce issue-first coordination

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
