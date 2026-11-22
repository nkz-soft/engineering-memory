"""Verify the installed stdio server using a synthetic offline profile."""

import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from engineering_memory.settings import workstation_native_process_variables

_REQUIRED_TOOLS = {"search_memory", "get_conversation"}
# Leave room in the 30-second budget for the SDK's bounded process-tree teardown.
_REQUEST_TIMEOUT = 23


def _environment(scratch: Path) -> dict[str, str]:
    environment = workstation_native_process_variables()
    environment.update(
        HOME=str(scratch),
        USERPROFILE=str(scratch),
        HOMEDRIVE=scratch.drive,
        HOMEPATH=str(scratch)[len(scratch.drive) :],
        USERNAME="engineering-memory-probe",
        USER="engineering-memory-probe",
        LOGNAME="engineering-memory-probe",
        PATH=os.defpath,
        APPDATA=str(scratch / "roaming"),
        LOCALAPPDATA=str(scratch / "local"),
        XDG_CONFIG_HOME=str(scratch / "config"),
        XDG_DATA_HOME=str(scratch / "data"),
        XDG_CACHE_HOME=str(scratch / "cache"),
        TEMP=str(scratch),
        TMP=str(scratch),
        TMPDIR=str(scratch),
        PYINSTALLER_RESET_ENVIRONMENT="1",
    )
    return environment


@contextmanager
def _quiet_sdk():
    # The SDK can include malformed wire data in its exception logs.
    loggers = [logging.getLogger(name) for name in ("mcp.client.stdio", "mcp.client.session")]
    original = [logger.disabled for logger in loggers]
    try:
        for logger in loggers:
            logger.disabled = True
        yield
    finally:
        for logger, disabled in zip(loggers, original, strict=True):
            logger.disabled = disabled


async def _list_tools(
    executable: Path, args: tuple[str, ...], scratch: Path, timeout: float
) -> str:
    environment = _environment(scratch)
    profile = (
        Path(environment["LOCALAPPDATA"]) / "EngineeringMemory/config"
        if os.name == "nt"
        else Path(environment["XDG_CONFIG_HOME"]) / "engineering-memory"
    )
    profile.mkdir(mode=0o700, parents=True)
    (profile / "app.env").write_text(
        "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=http://127.0.0.1:1\n",
        encoding="utf-8",
    )
    parameters = StdioServerParameters(
        command=str(executable), args=list(args), env=environment, cwd=scratch
    )
    with _quiet_sdk(), open(os.devnull, "w", encoding="utf-8") as quiet, anyio.fail_after(timeout):
        async with (
            stdio_client(parameters, errlog=quiet) as streams,
            ClientSession(*streams) as session,
        ):
            await session.initialize()
            tools = (await session.list_tools()).tools
            if {tool.name for tool in tools} >= _REQUIRED_TOOLS:
                return "passed"
            return "missing-tools"


def _probe(executable: Path, args: tuple[str, ...], *, timeout: float) -> str:
    try:
        if not executable.is_absolute() or not executable.is_file():
            return "failed"
        with tempfile.TemporaryDirectory(prefix="engineering-memory-mcp-") as temporary:
            return anyio.run(_list_tools, executable, args, Path(temporary), timeout)
    except TimeoutError:
        return "timeout"
    except Exception:
        return "failed"


def probe(executable: Path) -> str:
    return _probe(executable, ("serve",), timeout=_REQUEST_TIMEOUT)
