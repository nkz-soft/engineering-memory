"""Check the installed CLI and MCP transport from an unrelated working directory."""

import argparse
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters


async def smoke(executable: Path, version: str, scratch: Path) -> None:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("ENGINEERING_MEMORY_")
    }
    profile = scratch / "private profile"
    profile.mkdir()
    environment.update(
        LOCALAPPDATA=str(profile),
        XDG_CONFIG_HOME=str(profile),
        XDG_DATA_HOME=str(scratch / "data"),
    )
    config = profile / ("EngineeringMemory/config" if os.name == "nt" else "engineering-memory")
    config.mkdir(parents=True)
    (config / "app.env").write_text(
        "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=http://127.0.0.1:1\n",
        encoding="utf-8",
    )

    def command(*args: str) -> str:
        return subprocess.check_output(
            [str(executable), *args], cwd=scratch, env=environment, text=True, timeout=30
        )

    if command("--version").strip() != f"engineering-memory {version}":
        raise RuntimeError("Installed version mismatch")
    command("status", "--json")
    parameters = StdioServerParameters(
        command=str(executable), args=["serve"], env=environment, cwd=str(scratch)
    )
    with anyio.fail_after(30):
        async with Client(parameters, mode="legacy") as client:
            tools = (await client.list_tools()).tools
            if not {"get_conversation", "search_memory"} <= {tool.name for tool in tools}:
                raise RuntimeError(
                    "Installed MCP server did not expose search and source retrieval"
                )
            if not all(tool.annotations and tool.annotations.read_only_hint for tool in tools):
                raise RuntimeError("Installed MCP server exposed a non-read-only tool")
    print(f"Installed CLI {version}: version, offline status and read-only MCP verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable")
    parser.add_argument("version")
    args = parser.parse_args()
    executable = Path(args.executable).absolute()
    with TemporaryDirectory(prefix="engineering memory smoke ") as directory:
        anyio.run(smoke, executable, args.version, Path(directory))


if __name__ == "__main__":
    main()
