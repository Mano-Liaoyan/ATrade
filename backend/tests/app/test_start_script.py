"""`./start run` checks .env before it calls Docker Compose.

The test copies `start` to a temporary repository root and puts a fake `docker` on PATH. The fake writes its
arguments to a file, so the test sees whether Compose was called.
"""

import os
import shutil
import subprocess
from pathlib import Path

START_SCRIPT = Path(__file__).resolve().parents[3] / "start"
VALID_ENV = "ATRADE_POSTGRES_PASSWORD=test-password\nATRADE_TRADING_MODE=paper\n"
OLD_STACK_ENV = "ATRADE_API_HTTP_PORT=5181\nATRADE_IBKR_PAPER_ACCOUNT_ID=DU0000000\nATRADE_BROKER_ACCOUNT_MODE=Paper\n"


def run_start(
    tmp_path: Path, env_text: str | None, extra_env: dict[str, str] | None = None
) -> tuple[subprocess.CompletedProcess[str], Path]:
    repo_root = tmp_path / "repo"
    (repo_root / "deploy").mkdir(parents=True)
    shutil.copy(START_SCRIPT, repo_root / "start")
    (repo_root / ".env.example").write_text(VALID_ENV)
    if env_text is not None:
        (repo_root / ".env").write_text(env_text)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_calls = tmp_path / "docker_calls.txt"
    fake_docker = bin_dir / "docker"
    fake_docker.write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{docker_calls}"\n')
    fake_docker.chmod(0o755)
    result = subprocess.run(
        ["bash", str(repo_root / "start"), "run", "-d"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(extra_env or {}), "PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )
    return result, docker_calls


def test_calls_docker_compose_up_with_a_valid_env_file(tmp_path: Path) -> None:
    result, docker_calls = run_start(tmp_path, VALID_ENV)

    assert result.returncode == 0, result.stderr
    assert "compose" in docker_calls.read_text()
    assert "up --build -d" in docker_calls.read_text()


def test_stops_with_a_clear_message_when_the_postgres_password_is_missing(tmp_path: Path) -> None:
    result, docker_calls = run_start(tmp_path, "ATRADE_TRADING_MODE=paper\n")

    assert result.returncode == 1
    assert "ATRADE_POSTGRES_PASSWORD" in result.stderr
    assert ".env.example" in result.stderr
    assert not docker_calls.exists()


def test_stops_with_a_clear_message_when_the_postgres_password_is_empty(tmp_path: Path) -> None:
    result, docker_calls = run_start(tmp_path, "ATRADE_POSTGRES_PASSWORD=\n")

    assert result.returncode == 1
    assert "ATRADE_POSTGRES_PASSWORD" in result.stderr
    assert not docker_calls.exists()


def test_names_the_variables_of_the_old_stack(tmp_path: Path) -> None:
    result, docker_calls = run_start(tmp_path, OLD_STACK_ENV)

    assert result.returncode == 1
    assert "old ATrade stack" in result.stderr
    assert "ATRADE_API_HTTP_PORT" in result.stderr
    assert "ATRADE_IBKR_PAPER_ACCOUNT_ID" in result.stderr
    assert not docker_calls.exists()


def test_warns_about_old_variables_but_starts_when_the_required_ones_are_set(tmp_path: Path) -> None:
    result, docker_calls = run_start(tmp_path, VALID_ENV + "ATRADE_API_HTTP_PORT=5181\n")

    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stderr
    assert "ATRADE_API_HTTP_PORT" in result.stderr
    assert "compose" in docker_calls.read_text()


def test_password_in_the_process_environment_is_enough(tmp_path: Path) -> None:
    result, docker_calls = run_start(
        tmp_path, "ATRADE_TRADING_MODE=paper\n", extra_env={"ATRADE_POSTGRES_PASSWORD": "exported-password"}
    )

    assert result.returncode == 0, result.stderr
    assert "compose" in docker_calls.read_text()
