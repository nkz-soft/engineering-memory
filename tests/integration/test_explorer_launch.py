"""Smoke-test the installed explore entry point using an isolated profile."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest


def test_installed_explorer_serves_assets_and_requires_key(tmp_path):
    # Run the installed entry function directly so terminating the process also
    # stops the listener on Windows, where the console stub spawns a child.
    command = [sys.executable, "-c", "from engineering_memory.cli import main; main()", "explore"]
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("ENGINEERING_MEMORY_")
    }
    environment.update(
        ENGINEERING_MEMORY_HINDSIGHT__BASE_URL="http://127.0.0.1:1",
        ENGINEERING_MEMORY_ARCHIVE_ROOT=str(tmp_path / "archive"),
        LOCALAPPDATA=str(tmp_path),
        XDG_CONFIG_HOME=str(tmp_path),
        XDG_DATA_HOME=str(tmp_path),
    )

    with (
        ThreadPoolExecutor() as pool,
        subprocess.Popen(
            command,
            cwd=tmp_path,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as explorer,
    ):
        try:
            assert explorer.stdout is not None

            def startup_lines():
                return explorer.stdout.readline().strip(), explorer.stdout.readline().strip()

            address, credential = pool.submit(startup_lines).result(timeout=15)
            origin = address.removeprefix("Open ").rstrip("/")
            token = credential.removeprefix("Access key: ")
            assert origin.startswith("http://127.0.0.1:")
            assert len(token) >= 43 and token not in origin

            with httpx.Client(base_url=origin, trust_env=False, timeout=5) as client:
                assert client.get("/").status_code == 200
                for asset in ("explorer.css", "explorer.js"):
                    assert client.get(f"/assets/{asset}").status_code == 200

                payload = {"query": "Retries", "project": "orchard"}
                anonymous = client.post(
                    "/api/deep-recall", json=payload, headers={"Origin": origin}
                )
                assert anonymous.status_code == 401
                allowed = client.post(
                    "/api/deep-recall",
                    json=payload,
                    headers={"Origin": origin, "Authorization": f"Bearer {token}"},
                )
                assert allowed.status_code == 503
                assert allowed.json() == {"error": "synthesis_unconfigured"}
        finally:
            if explorer.poll() is None:
                explorer.terminate()
                try:
                    explorer.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    explorer.kill()

    with (
        httpx.Client(trust_env=False, timeout=2) as client,
        pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)),
    ):
        client.get(origin)
