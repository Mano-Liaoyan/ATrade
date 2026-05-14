---
name: annotations-to-prd-issues
description: Convert annotated issue feedback into clarified requirements, a PRD, and vertical-slice implementation issues **WITHOUT** starting implementation. Use when the user mentions fixing issues from annotations, review annotations, annotated feedback, or wants a parent-managed grill-with-docs -> PRD subagent -> issue subagent planning workflow.
---

# Annotations To PRD Issues

<what-to-do>

Use this skill to turn annotated feedback into planning artifacts only:

1. Identify the annotation source: PR review annotations, inline code comments, screenshots, issue comments, local notes, or a supplied file.
2. The parent agent runs the grilling session using `grill-with-docs` (**MUST TO DO**).
3. After all the uncertainty are resolved, the parent sends a handoff to a fresh PRD subagent running `to-prd`. You **MUST** use `caveman` to make sure your prd instructions are minimal and complete.
4. After the PRD subagent creates the PRD and the GitHub PRD issue, the parent sends that GitHub link plus prior decisions to a fresh issue subagent running `to-issues`. Make sure that this issue was assigned as a sub-issue of the PRD issue. You **MUST** also use `caveman` to make sure your issue instructions are minimal and complete.
5. Stop. Do **NOT** implement fixes.

## Hard rules

- No implementation during this workflow. Do not edit production code, tests, schemas, UI, or generated artifacts except documentation produced by the invoked planning skills.
- The grilling session is managed by the **parent** agent, not a subagent.
- The grilling session is a **MUST** to do, **ALWAYS** ask questions first you have something not quite understood.
- PRD generation and issue generation each run in their own fresh subagent.
- The parent agent is responsible for user interaction, compact handoffs, subagent orchestration, and final status.
- Ask the user only for information that cannot be discovered from annotations, repo docs, issue tracker context, or code exploration.
- Ask blocking questions one at a time. Do not dump a long questionnaire.
- Issues created by the issue subagent should be marked as a sub-issue of the PRD issue.
- Preserve the project language from `CONTEXT.md`, `CONTEXT-MAP.md`, and ADRs. If terminology is missing or ambiguous, let `grill-with-docs` resolve it.

</what-to-do>

<supporting-info>

## Workflow

### 1. Annotation intake

Collect the minimum needed context:

- Annotation source references, such as PR number, issue number, file path, screenshot, or pasted notes.
- The user's stated goal and any explicit non-goals.
- Any relevant domain docs from `docs/agents/domain.md`.
- Issue tracker conventions from `docs/agents/issue-tracker.md` and labels from `docs/agents/triage-labels.md`.

If no annotation source is available, ask the user for it before starting the grilling session.

### 2. Parent-managed grilling

The parent agent runs `grill-with-docs` directly:

- Inspect annotations and relevant repo/docs context.
- Identify only the questions blocking a correct fix plan.
- Explore the repo instead of asking when the answer is discoverable.
- Ask one blocking question at a time, with a recommended answer.
- Update domain docs inline only when `grill-with-docs` requires it.
- Maintain a compact clarification summary: resolved decisions, remaining blockers, changed docs, and terms of art.

When the grilling session ends, the parent prepares the PRD handoff itself. Include only information needed to generate the PRD.

### 3. PRD subagent

After the user confirms the clarification phase is complete enough, spawn a fresh subagent with `to-prd` instructions and this handoff:

- Annotation source summary.
- Resolved decisions and domain terms from the parent-managed grilling session.
- Remaining open questions, explicitly marked as out of scope or risks.
- Any docs or ADRs changed during grilling.
- Explicit instruction to return the PRD source path and the published GitHub issue link.
- Use `caveman` to ensure the handoff is minimal and complete for PRD generation.

The PRD subagent must create the PRD source under `docs/prd/`, publish it to the project issue tracker, and apply the normal PRD triage label.

### 4. Issue breakdown subagent

After the PRD subagent is done, spawn a fresh subagent with `to-issues` instructions and this handoff:

- PRD source path.
- Published PRD GitHub issue link from the previous step.
- Resolved decisions and domain terms from the grilling session.
- User-approved decisions from the PRD step, if any.
- Any out-of-scope items or risks that should not become implementation tickets.
- Use `caveman` to ensure the handoff is minimal and complete for issue generation.

The issue subagent must use the PRD GitHub issue link as the parent reference (each issue should be a sub-issue of the PRD issue), draft vertical-slice issues, quiz the user on granularity and dependencies, wait for approval, then publish issues in dependency order.

## Final response

Report only:

- Clarification outcome and any remaining blockers.
- PRD path and issue reference.
- Created implementation issue references.
- Confirmation that no implementation was performed.

</supporting-info>
