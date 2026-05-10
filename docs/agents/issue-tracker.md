# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub Issues in `Mano-Liaoyan/ATrade`. Use the GitHub connector when available, or the `gh` CLI when a workflow specifically needs local command-line behavior.

## Conventions

- **Create an issue**: create a GitHub issue with a clear title, Markdown body, and any relevant labels.
- **Read an issue**: fetch the issue body, labels, and comments.
- **List issues**: filter by state and label when a skill asks for a queue or triage set.
- **Comment on an issue**: add a normal GitHub issue comment.
- **Apply / remove labels**: update the issue's labels using the mappings in `docs/agents/triage-labels.md`.
- **Close**: close the GitHub issue with a short completion or non-actioning note.

Infer the repository from the local git remote when using `gh`; the configured origin is `https://github.com/Mano-Liaoyan/ATrade.git`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue in `Mano-Liaoyan/ATrade`.

## When a skill says "fetch the relevant ticket"

Fetch the corresponding GitHub issue, including comments and labels.
