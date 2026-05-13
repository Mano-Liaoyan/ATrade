---
name: parallel-github-issue-solver
description: Fetches ready-for-agent GitHub issues, parses each issue's explicit Blocked by section, builds an execution DAG from open blockers, solves unblocked issues with TDD in parallel subagents using per-issue git worktrees, then opens and merges one PR per issue. Use when the user wants to grab GitHub issues from a URL, solve multiple issues concurrently, schedule issue work by dependency, create PRs, merge PRs, or manage issue worktrees/branches.
---

# Parallel GitHub Issue Solver

## Quick start

When given a GitHub repository or issues URL:

1. Parse the owner/repo and issue selection scope.
2. Automatically fetch all open issues labeled `ready-for-agent` unless the user gave explicit issue numbers.
3. Parse each issue's explicit `## Blocked by` section and verify each referenced blocker with `gh`.
4. Generate a DAG where edge `A -> B` means issue `A` must be completed before issue `B`.
5. Execute the DAG in topological waves: run every issue in the current unblocked wave in parallel, then synchronize, merge, refresh base, and continue with newly unblocked issues.
6. For each issue, create a local branch and git worktree under `./.worktree/` only when its execution wave starts.
7. Run one subagent per unblocked issue **in parallel**, instructing each subagent to use `/skill:tdd`.
8. For each solved issue, push its branch, create a PR, merge the PR, then delete only the local branch/worktree.
9. Never delete the remote PR branch.

## Workflow

### 1. Discover the queue

- For a repo issues URL such as `https://github.com/OWNER/REPO/issues`, list every open issue labeled `ready-for-agent`:

```bash
gh issue list --repo OWNER/REPO --state open --label ready-for-agent --limit 200 --json number,title,labels,assignees,milestone,body,url
```

- For a single issue URL, inspect it with `gh issue view ISSUE --repo OWNER/REPO` and ask the user to confirm or add more issues.
- For multiple issue URLs, extract each issue number and confirm the set.
- If the user explicitly asks for a different label or issue set, use that scope instead of `ready-for-agent`.
- If no `ready-for-agent` issues are found, report that and stop.
- Do not begin implementation until the execution DAG has been shown and the user confirms it.

### 2. Parse explicit blockers

Build a dependency record for every fetched issue before starting implementation.

Only use the issue body's `## Blocked by` section to determine issue-to-issue dependencies. Do not infer dependency edges from comments, labels, assignees, milestones, PRs, branch names, failed checks, file overlap, or related issue language elsewhere in the body.

Recognized forms:

```markdown
## Blocked by

- https://github.com/OWNER/REPO/issues/53
- https://github.com/OWNER/REPO/issues/55
```

```markdown
## Blocked by

None - can start immediately.
```

For each blocker URL or issue reference in `## Blocked by`:

- Extract the referenced owner, repo, and issue number.
- Check current state with `gh issue view ISSUE --repo OWNER/REPO --json number,state,title,url`.
- If the referenced issue is `CLOSED`, ignore it and do not add a DAG edge.
- If the referenced issue is not closed, treat it as an active blocker.
- If `gh` cannot determine the referenced issue state, treat it as blocking until verified.

Classify each active blocker:

- `internal-open`: the blocker is one of the fetched queue issues and is not closed. Add a DAG edge from blocker to blocked.
- `external-open`: the blocker is not in the fetched queue and is not closed. Hold the blocked issue out of executable waves.
- `unknown-state`: `gh` could not verify the blocker state. Hold the blocked issue out of executable waves.

Rules:

- If `## Blocked by` is missing, report the issue as malformed for this workflow and ask before executing it.
- If `## Blocked by` contains `None`, `None - can start immediately.`, or equivalent plain `None` text, treat the issue as having no blockers.
- Add DAG edges only from active `internal-open` blockers.
- Do not add edges for closed blockers.
- Keep issues with `external-open` or `unknown-state` blockers out of executable waves until the blocker closes or the user explicitly overrides.
- If the graph contains a cycle, report the cycle and stop. Do not execute until the cycle is broken or the user chooses an override.

### 3. Generate the execution DAG

Produce a concise execution plan before implementation:

```text
Ready-for-agent queue:
- #101 Title
- #102 Title

DAG edges:
- #101 -> #102 because #102 lists #101 in `## Blocked by` and #101 is open

Execution waves:
- Wave 1: #101, #103
- Wave 2: #102

Held issues:
- #104 blocked by external open issue OWNER/OTHER#88
```

The DAG must include:

- Every fetched issue as a node, unless it is superseded, closed, or not actually ready.
- Edge direction as `blocker -> blocked`.
- A topological wave plan showing which issues can run in parallel.
- Ignored closed blockers, when relevant.
- Held issues with external open or unknown-state blockers.
- Issues requiring user confirmation because `## Blocked by` is missing or malformed.

### 4. Prepare worktrees per wave

Before creating branches for each wave:

- Verify the working tree is clean with `git status --short`.
- Fetch the default branch: `git fetch origin`.
- Create `./.worktree/` if needed.
- Make sure all dependencies for the wave have merged into the base branch.
- Create worktrees from the refreshed base branch, not from a stale branch created before dependency PRs merged.

For each issue:

```bash
git worktree add ./.worktree/issue-123 -b issue-123 origin/main
```

Use the repository's actual default branch if it is not `main`.

### 5. Run parallel TDD subagents

Use the `pi-subagents` capability. First inspect available agents with `subagent({"action":"list"})`.

Run a parallel subagent task per issue in the current wave with `cwd` set to that issue's worktree. Each task must say:

- Load and follow `/skill:tdd`.
- Read the GitHub issue with `gh issue view`.
- Respect the DAG: this issue's dependencies have already merged; do not start work for issues in later waves.
- Reproduce the bug or specify the missing behavior with a failing test first.
- Implement the smallest change to pass.
- Run the relevant test/validation commands.
- Commit only the changes for that issue.
- Report commit SHA, tests run, and any risk.

Prefer explicit worktree directories over subagent-managed temporary worktrees so all work happens under `./.worktree/`.

### 6. Synchronize after each wave

After all subagents in a wave finish:

- Review each report for tests, commit SHA, risk, and any newly discovered blockers.
- If an issue report claims a new dependency, verify whether that dependency is recorded in the blocked issue's `## Blocked by` section. Do not update the DAG from inferred or ad hoc dependency claims.
- If an issue failed but other issues in the wave succeeded, continue only for successful issues that do not depend on the failed issue. Ask before merging if the failure changes downstream ordering.
- Merge successful PRs before starting the next wave so dependent work begins from the updated base.
- Refresh the base branch and re-check blocker issue states with `gh` before creating the next wave's worktrees. Closed blockers should be ignored at that point.

### 7. Create and merge PRs

For each completed issue worktree:

```bash
git -C ./.worktree/issue-123 push -u origin issue-123
gh pr create --repo OWNER/REPO --head issue-123 --base main --title "Fix #123: ..." --body "Closes #123"
gh pr merge PR_NUMBER --merge
```

Use the repo's normal merge method if known. After merge, clean up locally only:

```bash
git worktree remove ./.worktree/issue-123
git branch -D issue-123
```

Do **not** pass `--delete-branch` to `gh pr merge`; it may delete the remote PR branch. Do **not** run `git push origin --delete issue-123`.

## Safety checks

- Stop and ask if `gh auth status` fails.
- Stop and ask if the base branch is protected and PR merge requires review or checks that are not complete.
- Stop and ask if the DAG has cycles, missing or malformed `## Blocked by` sections, unknown blocker states, or external open blockers that prevent execution.
- If one issue fails while others succeed, continue merging successful PRs only after reporting the failed issue and checking whether downstream waves are affected.
- Do not create dependency edges from file overlap or conceptual overlap. Only warn if parallel work is likely to conflict operationally.
- Never execute a blocked issue just because there is an idle subagent. The DAG determines parallelism and synchronization points.
