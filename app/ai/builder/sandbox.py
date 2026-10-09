"""Docker-only, network-isolated execution for Admin Builder project tests."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
from uuid import uuid4

from .project_files import normalize_project_files


class SandboxUnavailable(RuntimeError):
    """The required restricted container runtime is not ready."""


class SandboxNoTests(ValueError):
    """The candidate has no supported Python test files."""


_PINNED_IMAGE = re.compile(r"^(?:[A-Za-z0-9./:_-]+@)?sha256:[a-f0-9]{64}$")
_PASSED_RE = re.compile(r"\b(\d+)\s+passed\b")
_FAILED_RE = re.compile(r"\b(\d+)\s+(?:failed|error|errors)\b")


def run_project_tests(files, *, image: str, timeout_seconds: int = 60):
    """Run only pytest inside a disposable, non-root, no-network container."""
    normalized = normalize_project_files(files)
    if not any(
        PurePosixPath(item["path"]).name.startswith("test_")
        or PurePosixPath(item["path"]).name.endswith("_test.py")
        for item in normalized
        if item["path"].endswith(".py")
    ):
        raise SandboxNoTests("Add a Python test file before running the sandbox.")
    if not image or not _PINNED_IMAGE.fullmatch(image):
        raise SandboxUnavailable("Configure a sandbox image pinned by immutable SHA-256 digest.")
    docker = shutil.which("docker")
    if not docker:
        raise SandboxUnavailable("Docker is not installed or available to the application process.")

    timeout_seconds = max(5, min(int(timeout_seconds), 120))
    container_name = f"nexhaat-builder-{uuid4().hex[:20]}"
    with tempfile.TemporaryDirectory(prefix="nexhaat-builder-") as temp_dir:
        root = Path(temp_dir).resolve()
        for item in normalized:
            destination = root.joinpath(*PurePosixPath(item["path"]).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(item["content"], encoding="utf-8", newline="\n")
            try:
                os.chmod(destination, 0o444)
            except OSError:
                pass
        try:
            result = subprocess.run(
                [
                    docker, "run", "--rm", "--pull=never", "--name", container_name,
                    "--network=none", "--read-only", "--cap-drop=ALL",
                    "--security-opt=no-new-privileges:true", "--pids-limit=32",
                    "--memory=256m", "--cpus=0.5", "--user=65532:65532",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
                    "--env", "PYTHONDONTWRITEBYTECODE=1",
                    "--env", "PYTHONHASHSEED=0",
                    "--mount", f"type=bind,source={root},target=/workspace,readonly",
                    "--workdir", "/workspace",
                    image,
                    "python", "-I", "-m", "pytest", "-q",
                    "-p", "no:cacheprovider", "--basetemp=/tmp/pytest",
                ],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
            passed = result.returncode == 0
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            passed_matches = _PASSED_RE.findall(output)
            failed_matches = _FAILED_RE.findall(output)
            return {
                "status": "passed" if passed else "failed",
                "exit_code": int(result.returncode),
                "passed_count": int(passed_matches[-1]) if passed_matches else 0,
                "failed_count": sum(int(value) for value in failed_matches),
                "summary": (
                    "Sandbox tests passed."
                    if passed else "Sandbox tests failed; raw output was discarded."
                ),
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "exit_code": None,
                "summary": "Sandbox test execution exceeded the time limit.",
            }
        except (OSError, subprocess.SubprocessError) as error:
            raise SandboxUnavailable(
                f"Sandbox runner failed safely ({type(error).__name__})."
            ) from error
        finally:
            try:
                subprocess.run(
                    [docker, "rm", "--force", container_name],
                    capture_output=True,
                    timeout=10,
                    check=False,
                    shell=False,
                )
            except (OSError, subprocess.SubprocessError):
                pass
