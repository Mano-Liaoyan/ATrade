---
name: github-coordination
description: Use when multiple agents coordinate through GitHub issues, labels, draft pull requests, and resumable blocked work without waiting idly for human approval.
---

# GitHub Coordination

## Overview

GitHub is the shared queue, memory, and audit trail for autonomous work.

**Core principle:** blocked work must remain resumable while agents keep moving on other ready work.

## When to Use

- coordinating 2 or more active issues
- tracking blocked work that needs human approval
- reconciling issue, PR, and plan state

## Workflow

1. Represent each unit of work as one issue.
2. Claim it with workflow and role labels.
3. Open a draft PR as soon as a branch exists.
4. If blocked, switch the issue to `agent:needs-human` or `agent:blocked`.
5. Leave a short unblock note and a resume note.
6. Move to another `agent:ready` issue.
7. When unblocked, move back to `agent:resume-ready` and continue.

## Recommended Labels

- `agent:ready`
- `agent:claimed`
- `agent:in-progress`
- `agent:needs-human`
- `agent:blocked`
- `agent:resume-ready`
- `agent:review`
- `agent:merged`
- `agent:docs-required`
- `agent:trivial`

Recommended role labels:

- `role:architect`
- `role:senior-engineer`
- `role:senior-test-engineer`
- `role:devops`
- `role:scrum-master`
- `role:code-reviewer`
- `role:handyman`
- `role:onboarder`

## Common Mistakes

- leaving blocked work only in chat history
- waiting idly instead of switching to another ready issue
- changing issue state without updating the role plan
- using PR state alone as the scheduler
