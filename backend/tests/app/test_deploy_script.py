"""`scripts/deploy` deploys only commits of origin/main.

The test makes a bare origin repository and a clone of it with `scripts/deploy` and a fake `start`. The fake
writes its arguments to a file, so the test sees whether the start was called.
"""

import os
import shutil
import subprocess
from pathlib import Path

DEPLOY_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "deploy"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env={**os.environ, **GIT_ENV}
    )
    return result.stdout.strip()


def commit_file(repo: Path, name: str) -> str:
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "commit", "--quiet", "-m", name)
    return git(repo, "rev-parse", "HEAD")


def make_server_checkout(tmp_path: Path, start_calls: Path) -> Path:
    """Returns a clone of a bare origin. The clone has the deploy script and a fake start in its first commit."""
    author = tmp_path / "author"
    author.mkdir()
    git(author, "init", "--quiet", "--initial-branch=main")
    (author / "scripts").mkdir()
    shutil.copy(DEPLOY_SCRIPT, author / "scripts" / "deploy")
    (author / "start").write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{start_calls}"\n')
    (author / "start").chmod(0o755)
    (author / ".gitignore").write_text(".env\n")
    git(author, "add", ".")
    git(author, "commit", "--quiet", "-m", "first")
    git(tmp_path, "clone", "--quiet", "--bare", str(author), "origin.git")
    git(author, "remote", "add", "origin", str(tmp_path / "origin.git"))
    git(tmp_path, "clone", "--quiet", str(tmp_path / "origin.git"), "server")
    server = tmp_path / "server"
    (server / ".env").write_text("ATRADE_POSTGRES_PASSWORD=test-password\n")
    return server


def run_deploy(
    server: Path, args: list[str], extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(server / "scripts" / "deploy"), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **GIT_ENV, **(extra_env or {})},
    )


def test_checks_out_a_new_commit_of_main_and_starts_in_the_background(tmp_path: Path) -> None:
    start_calls = tmp_path / "start_calls.txt"
    server = make_server_checkout(tmp_path, start_calls)
    new_commit = commit_file(tmp_path / "author", "change.txt")
    git(tmp_path / "author", "push", "--quiet", "origin", "main")

    result = run_deploy(server, [new_commit])

    assert result.returncode == 0, result.stderr
    assert git(server, "rev-parse", "HEAD") == new_commit
    assert start_calls.read_text() == "run --detach --wait\n"


def test_reads_the_commit_from_the_ssh_forced_command(tmp_path: Path) -> None:
    start_calls = tmp_path / "start_calls.txt"
    server = make_server_checkout(tmp_path, start_calls)
    commit = git(server, "rev-parse", "HEAD")

    result = run_deploy(server, [], {"SSH_ORIGINAL_COMMAND": commit})

    assert result.returncode == 0, result.stderr
    assert start_calls.exists()


def test_refuses_a_commit_that_is_not_on_main(tmp_path: Path) -> None:
    start_calls = tmp_path / "start_calls.txt"
    server = make_server_checkout(tmp_path, start_calls)
    author = tmp_path / "author"
    git(author, "checkout", "--quiet", "-b", "feature")
    feature_commit = commit_file(author, "feature.txt")
    git(author, "push", "--quiet", "origin", "feature")

    result = run_deploy(server, [feature_commit])

    assert result.returncode == 1
    assert "not on origin/main" in result.stderr
    assert not start_calls.exists()


def test_refuses_a_value_that_is_not_a_full_sha(tmp_path: Path) -> None:
    start_calls = tmp_path / "start_calls.txt"
    server = make_server_checkout(tmp_path, start_calls)

    result = run_deploy(server, [], {"SSH_ORIGINAL_COMMAND": "main; rm -rf /"})

    assert result.returncode == 2
    assert "40-character SHA" in result.stderr
    assert not start_calls.exists()


def test_stops_with_a_clear_message_when_env_is_missing(tmp_path: Path) -> None:
    start_calls = tmp_path / "start_calls.txt"
    server = make_server_checkout(tmp_path, start_calls)
    (server / ".env").unlink()

    result = run_deploy(server, [git(server, "rev-parse", "HEAD")])

    assert result.returncode == 1
    assert ".env not found" in result.stderr
    assert not start_calls.exists()
