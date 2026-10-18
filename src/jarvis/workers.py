import os
import subprocess
import uuid
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class WorkerResult:
    exit_code: int
    stdout: str
    stderr: str
    error: Optional[str] = None

class WorkerManager:
    """Manages isolated local/Docker environments for task execution."""

    def __init__(self, use_docker: bool = True):
        self.use_docker = use_docker
        if not self.use_docker:
            raise RuntimeError("Docker isolation is mandatory. Cannot disable use_docker.")
        self.workspace_base = Path(tempfile.gettempdir()) / "jarvis_workspaces"
        self.workspace_base.mkdir(parents=True, exist_ok=True)

        # Verify docker availability if requested
        if self.use_docker:
            try:
                subprocess.run(["docker", "--version"], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise RuntimeError("Docker is required for isolated execution, but was not found.")

    def create_workspace(self) -> str:
        """Create a new isolated workspace directory."""
        workspace_id = str(uuid.uuid4())
        path = self.workspace_base / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def execute(self, command: list[str], workspace_path: str, timeout: int = 300) -> WorkerResult:
        """Execute a command either in Docker or natively if explicitly configured for testing."""
        return self._execute_docker(command, workspace_path, timeout)

    def _execute_docker(self, command: list[str], workspace_path: str, timeout: int) -> WorkerResult:
        """Execute a command inside a restricted Python Docker container."""
        # Note: In production this would use the `docker` python SDK or more robust subprocess wrappers.
        # This implementation binds the workspace and restricts networking and privileges.
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "512m",
            "--cpus", "0.5",
            "--user", "1000:1000", # Run as non-root
            "-v", f"{workspace_path}:/workspace",
            "-w", "/workspace",
            "python:3.11-slim"
        ] + command

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return WorkerResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
        except subprocess.TimeoutExpired as e:
            return WorkerResult(exit_code=124, stdout="", stderr="", error=f"Timeout after {timeout}s: {e}")
        except Exception as e:
            return WorkerResult(exit_code=-1, stdout="", stderr="", error=str(e))
