"""Manage the workstation backend through Docker Compose."""

import ctypes
import re
import shutil
import subprocess
import sys

import typer

from engineering_memory import workstation
from engineering_memory.settings import SettingsError, workstation_subprocess_environment

app = typer.Typer(help="Manage the installed workstation backend.", no_args_is_help=True)
MIN_COMPOSE = (2, 24, 4)


class StackError(RuntimeError):
    """An operator-facing error that contains no subprocess output."""


deployment_file = workstation.deployment_file


def run_stack(action: str) -> None:
    docker = shutil.which("docker")
    if docker is None:
        raise StackError("Install Docker with the Docker Compose plugin.")

    if sys.platform == "win32" and workstation.is_installed():
        # This standalone CLI only launches host Docker after this point.
        if not ctypes.windll.kernel32.SetDllDirectoryW(None):
            raise StackError("Could not set the native Docker library search path.")

    def run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [docker, *args],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                check=False,
                env=workstation_subprocess_environment(),
            )
        except subprocess.TimeoutExpired:
            raise StackError("Docker timed out. Check the daemon and retry.") from None
        except OSError:
            raise StackError("Docker could not start. Check the Docker installation.") from None

    compose_version = run(["compose", "version", "--short"])
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", compose_version.stdout.strip())
    if compose_version.returncode or not match or tuple(map(int, match.groups())) < MIN_COMPOSE:
        raise StackError("Install Docker Compose 2.24.4 or newer.")
    daemon = run(["info", "--format", "{{.OSType}} {{.ServerVersion}}"])
    if daemon.returncode:
        raise StackError("Start Docker and check permissions to access the daemon.")
    os_type, _, engine_version = daemon.stdout.strip().partition(" ")
    if os_type != "linux":
        raise StackError("Configure Docker to run Linux containers.")
    engine_major = engine_version.partition(".")[0]
    if not engine_major.isdecimal() or int(engine_major) < 28:
        raise StackError("Install Docker Engine 28 or newer for loopback-only port publishing.")

    profile, _ = workstation.locations()
    env_file = profile / "compose.env"
    if not env_file.is_file():
        raise StackError("Create the private compose.env using the workstation setup guide.")
    compose = deployment_file()
    base = [
        "compose",
        "--project-name",
        "engineering-memory-workstation",
        "--project-directory",
        str(compose.parent),
        "--env-file",
        str(env_file),
        "--file",
        str(compose),
    ]
    if action in {"check", "start"}:
        if run([*base, "config", "--quiet"]).returncode:
            raise StackError("Check the required settings and port numbers in compose.env.")
        if action == "check":
            typer.echo("Docker and the Compose configuration are ready.")
            return
        result = run([*base, "up", "-d", "--wait", "--wait-timeout", "900"], timeout=1500)
        if result.returncode:
            raise StackError(
                "Backend startup failed. Check port availability, Docker resources, "
                "image access and provider settings, then retry."
            )
        typer.echo("Workstation backend is ready.")
        return

    arguments = ["stop"] if action == "stop" else ["ps", "--all"]
    result = run([*base, *arguments], timeout=120)
    if result.returncode:
        raise StackError(f"Backend {action} failed. Check Docker and compose.env.")
    typer.echo("Workstation backend stopped." if action == "stop" else result.stdout.rstrip())


def _execute(action: str) -> None:
    try:
        run_stack(action)
    except (StackError, SettingsError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None


@app.command()
def check() -> None:
    """Check Docker, Compose and workstation configuration."""
    _execute("check")


@app.command()
def start() -> None:
    """Start services and wait for readiness."""
    _execute("start")


@app.command()
def stop() -> None:
    """Stop services and preserve the backend volume."""
    _execute("stop")


@app.command()
def status() -> None:
    """Show backend service status."""
    _execute("status")
