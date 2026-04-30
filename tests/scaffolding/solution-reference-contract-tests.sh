#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

assert_path_exists() {
  local path="$1"

  if [[ ! -e "$path" ]]; then
    printf 'expected path to exist: %s\n' "$path" >&2
    return 1
  fi
}

assert_solution_membership_matches_projects() {
  local slnx_projects
  local csproj_files
  slnx_projects="$(mktemp)"
  csproj_files="$(mktemp)"

  (
    cd "$repo_root"
    dotnet sln ATrade.slnx list | sed '1,2d' | sed '/^$/d' | sort >"$slnx_projects"
    find src tests workers -name '*.csproj' | sort >"$csproj_files"
  )

  if ! diff -u "$csproj_files" "$slnx_projects"; then
    printf 'ATrade.slnx membership must match all active src/tests/workers projects.\n' >&2
    rm -f "$slnx_projects" "$csproj_files"
    return 1
  fi

  rm -f "$slnx_projects" "$csproj_files"
}

assert_no_stale_active_sln_guidance() {
  python3 - "$repo_root" <<'PY'
import re
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
active_roots = [
    repo_root / "README.md",
    repo_root / "PLAN.md",
    repo_root / "AGENTS.md",
    repo_root / "scripts",
    repo_root / "docs",
    repo_root / "tasks" / "CONTEXT.md",
    repo_root / "tests",
    repo_root / "src",
]
skip_parts = {"bin", "obj", "node_modules", ".git"}
legacy_reference = re.compile(r"ATrade\.sln\b")
stale_command = re.compile(r"dotnet\s+(?:build|test|sln(?:\s+\S+)?)\s+[^\n]*ATrade\.sln\b")
allowed_legacy_context = (
    "non-authoritative",
    "compatibility",
    "legacy",
    "retained only",
    "older tooling",
    "remains temporarily",
    "instead of adding new active",
    'File.Exists(Path.Combine(current.FullName, "ATrade.sln"))',
)

violations: list[str] = []
command_violations: list[str] = []

for root in active_roots:
    if not root.exists():
        continue
    paths = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    for path in paths:
        rel = path.relative_to(repo_root)
        if any(part in skip_parts for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if stale_command.search(line):
                command_violations.append(f"{rel}:{line_number}:{line.strip()}")
            if legacy_reference.search(line) and not any(token in line for token in allowed_legacy_context):
                violations.append(f"{rel}:{line_number}:{line.strip()}")

if command_violations:
    print("Active build/test/list guidance must use ATrade.slnx, not the legacy solution file:", file=sys.stderr)
    print("\n".join(command_violations), file=sys.stderr)
    raise SystemExit(1)

if violations:
    print("Unclassified active legacy-solution references found; use ATrade.slnx or document an explicit compatibility exception:", file=sys.stderr)
    print("\n".join(violations), file=sys.stderr)
    raise SystemExit(1)
PY
}

main() {
  assert_path_exists "$repo_root/ATrade.slnx"
  assert_path_exists "$repo_root/ATrade.sln" # legacy compatibility artifact
  assert_solution_membership_matches_projects
  assert_no_stale_active_sln_guidance
}

main "$@"
