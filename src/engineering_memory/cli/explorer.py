"""Foreground launch for the local memory explorer."""

import secrets
import socket
from contextlib import ExitStack

import typer
import uvicorn

from engineering_memory.api.explorer import create_explorer_app
from engineering_memory.cli import runtime


def run_explorer() -> None:
    with ExitStack() as resources:
        access = runtime.make_read_access(resources)
        status = runtime.make_explorer_status(resources)
        listener = resources.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        host, port = listener.getsockname()
        authority = f"{host}:{port}"
        token = secrets.token_urlsafe(32)
        app = create_explorer_app(access, token=token, authority=authority, read_status=status.read)
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host=host,
                port=port,
                access_log=False,
                proxy_headers=False,
                log_level="warning",
                ws="none",
                lifespan="off",
            )
        )
        typer.echo(f"Open http://{authority}/")
        typer.echo(f"Access key: {token}")
        server.run(sockets=[listener])
