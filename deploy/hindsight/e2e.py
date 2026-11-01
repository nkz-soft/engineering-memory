"""Required credential-free import/recall gate, with testcontainers isolation.

The parent bounds the whole worker (including image pulls), then removes only
resources labelled with this run's random identity, even after a worker timeout.
"""

import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

import docker
import httpx
import yaml
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

ROOT = Path(__file__).resolve().parents[2]
LABEL = "engineering-memory.e2e-run"
MODULE = "tests.integration.test_import_recall_e2e"
REQUIRED = {
    "test_import_and_recall",
    "test_pipeline_known_repository_and_tags",
    "test_wire_timestamp_omission_is_detected",
    "test_reimport_unchanged",
    "test_reimport_state_loss",
    "test_reimport_changed",
}


def verify_report(root):
    cases = list(root.iter("testcase"))
    identities = [(c.get("classname"), c.get("name")) for c in cases]
    if (
        not {(MODULE, name) for name in REQUIRED} <= set(identities)
        or len(identities) != len(set(identities))
        or any(c.find(o) is not None for c in cases for o in ("skipped", "failure", "error"))
    ):
        raise ValueError("end-to-end gate incomplete or nonpassing")


def wait_ready(url, deadline):
    with httpx.Client(timeout=5, trust_env=False) as client:
        while time.monotonic() < deadline:
            try:
                if client.get(url).is_success:
                    return
            except httpx.TransportError:
                pass
            time.sleep(1)
    raise TimeoutError("end-to-end dependency readiness deadline exceeded")


def cleanup(identity):
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--cleanup", identity],
        check=True,
        timeout=90,
    )


def cleanup_resources(identity):
    # Exact random label, never a project-wide prune. Attempt all owned resources.
    client = docker.from_env(timeout=15)
    errors = []
    try:
        filters = {"label": f"{LABEL}={identity}"}
        for collection, kwargs, remove_kwargs in [
            (
                client.containers,
                {"all": True, "filters": filters, "sparse": True},
                {"force": True, "v": True},
            ),
            (client.networks, {"filters": filters}, {}),
        ]:
            try:
                resources = collection.list(**kwargs)
            except Exception as error:
                errors.append(error)
                continue
            for resource in resources:
                try:
                    resource.remove(**remove_kwargs)
                except docker.errors.NotFound:
                    pass  # The worker or reaper already removed this resource.
                except Exception as error:
                    errors.append(error)
    finally:
        client.close()
    if errors:
        raise ExceptionGroup("end-to-end cleanup failed", errors)


def worker(identity, directory):
    labels = {LABEL: identity}
    canonical = yaml.safe_load((ROOT / "deploy/hindsight/service.yaml").read_text())
    service = canonical["services"]["hindsight"]
    contract = yaml.safe_load((ROOT / "deploy/hindsight/compose.contract.yaml").read_text())
    environment = {
        **service["environment"],
        **contract["services"]["hindsight"]["environment"],
        "HINDSIGHT_API_WORKER_ID": identity,
    }
    deadline = time.monotonic() + 600
    with ExitStack() as stack:
        network = stack.enter_context(
            Network(docker_client_kw={"timeout": 15}, docker_network_kw={"labels": labels})
        )
        fixture = stack.enter_context(
            DockerContainer(
                contract["services"]["extraction"]["image"],
                docker_client_kw={"timeout": 15},
                network=network,
                network_aliases=["extraction"],
                labels=labels,
            )
            .with_copy_into_container(
                ROOT / "tests/integration/hindsight_contract/llm.py", "/fixture/llm.py"
            )
            .with_command(["python", "/fixture/llm.py"])
            .with_exposed_ports(8080)
        )
        fixture_url = f"http://{fixture.get_container_host_ip()}:{fixture.get_exposed_port(8080)}"
        wait_ready(fixture_url + "/stats", deadline)
        engine = stack.enter_context(
            DockerContainer(
                service["image"],
                docker_client_kw={"timeout": 15},
                network=network,
                env=environment,
                shm_size=service["shm_size"],
                labels=labels,
            ).with_exposed_ports(8888)
        )
        url = f"http://{engine.get_container_host_ip()}:{engine.get_exposed_port(8888)}"
        wait_ready(url + "/health/ready", deadline)
        (Path(directory) / "ready").touch()
        report = Path(directory) / "results.xml"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_import_recall_e2e.py",
                "-q",
                "--tb=short",
                f"--junitxml={report}",
            ],
            cwd=ROOT,
            env={
                **os.environ,
                "ENGINEERING_MEMORY_LIVE_E2E": "1",
                "ENGINEERING_MEMORY_LIVE_STORE_URL": url,
                "CONTRACT_FIXTURE_URL": fixture_url,
            },
            check=True,
            # Leave the parent time to reap a timed-out pytest and close contexts.
            timeout=min(420, max(1, deadline + 360 - time.monotonic())),
        )
        verify_report(ET.parse(report).getroot())


def supervise(command, ready):
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT)
    try:
        while not ready.exists():
            code = process.poll()
            if code is not None:
                raise subprocess.CalledProcessError(code or 1, command)
            if time.monotonic() - started >= 600:
                raise subprocess.TimeoutExpired(command, 600)
            time.sleep(0.2)
        code = process.wait(timeout=max(1, 1020 - (time.monotonic() - started)))
        if code:
            raise subprocess.CalledProcessError(code, command)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=15)


def main():
    identity = "e2e-" + uuid4().hex
    with tempfile.TemporaryDirectory(prefix="memory-e2e-") as directory:
        try:
            supervise(
                [sys.executable, str(Path(__file__).resolve()), "--worker", identity, directory],
                Path(directory) / "ready",
            )
        finally:
            cleanup(identity)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cleanup":
        cleanup_resources(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "--worker":
        worker(sys.argv[2], sys.argv[3])
    else:
        main()
