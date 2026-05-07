---
name: ask-and-plan
description: Runs an ask-then-plan workflow that clarifies requirements using /grill-me, then creates small Taskplane packets using /create-taskplane-task. Use when the user has several requirements, wants to be grilled before planning, asks to convert requirements into Taskplane tasks, or invokes ask-and-plan.
---

# Ask And Plan

Use this skill to turn rough requirements into executable Taskplane work after
reaching shared understanding with the user.

## Quick start

1. Load project context and any relevant skills.
2. Use /grill-me to ask questions
3. Inspect the codebase/docs instead of asking questions the repository can answer.
4. Continue until the requirements can be decomposed safely.
5. Create small Taskplane packets using /create-taskplane-task.

Do not implement the planned product changes unless the user explicitly asks for
implementation rather than task staging.
