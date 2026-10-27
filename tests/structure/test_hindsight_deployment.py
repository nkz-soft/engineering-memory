"""Validate deployment behavior without a daemon, credentials or a live service."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

COMPOSE = Path(__file__).resolve().parents[2] / "deploy/hindsight/compose.yaml"


def test_local_deployment_has_persistent_private_engine_and_proxy_route():
    assert COMPOSE.is_file(), "the development deployment has not been implemented"
    config = yaml.safe_load(COMPOSE.read_text())
    assert set(config["services"]) == {"hindsight"}
    service = config["services"]["hindsight"]
    assert "@sha256:" in service["image"] and ":latest" not in service["image"]
    assert service["ports"] == ["127.0.0.1:${HINDSIGHT_DEV_PORT:-8888}:8888"]
    assert service["volumes"] == ["hindsight-data:/home/hindsight/.pg0"]
    assert "hindsight-data" in config["volumes"]
    assert service["shm_size"] == "1gb"
    env = service["environment"]
    assert env["HINDSIGHT_API_LLM_PROVIDER"] == "openai"
    assert env["HINDSIGHT_API_EMBEDDINGS_PROVIDER"] == "local"
    assert env["HINDSIGHT_API_RERANKER_PROVIDER"] == "local"
    assert env["HINDSIGHT_API_WORKER_ID"]
    assert "healthcheck" in service


def compose_run(*arguments, omit=()):
    if not shutil.which("docker"):
        pytest.skip("Compose validation is optional; Docker CLI is not installed")
    env = {k: v for k, v in os.environ.items() if not k.startswith("HINDSIGHT_")}
    env.update(
        {
            "HINDSIGHT_API_LLM_BASE_URL": "http://proxy.invalid:4000/v1",
            "HINDSIGHT_API_LLM_MODEL": "synthetic-alias",
            "HINDSIGHT_API_LLM_API_KEY": "synthetic-proxy-key",
        }
    )
    for key in omit:
        env.pop(key, None)
    version = subprocess.run(["docker", "compose", "version"], capture_output=True, env=env)
    if version.returncode:
        pytest.skip("Compose plugin not installed; offline tests need no Docker")
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), *arguments],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_compose_renders_effective_private_ports_and_volume():
    assert COMPOSE.is_file()
    result = compose_run("config", "--format", "json")
    assert result.returncode == 0
    config = json.loads(result.stdout)
    service = config["services"]["hindsight"]
    assert len(service["ports"]) == 1
    assert service["ports"][0]["host_ip"] == "127.0.0.1"
    assert service["ports"][0]["target"] == 8888
    assert service["environment"]["HINDSIGHT_API_LLM_MODEL"] == "synthetic-alias"
    assert service["volumes"][0]["type"] == "volume"


@pytest.mark.parametrize("missing", ["HINDSIGHT_API_LLM_BASE_URL", "HINDSIGHT_API_LLM_MODEL"])
def test_missing_proxy_configuration_fails_without_echoing_secret(missing):
    assert COMPOSE.is_file()
    result = compose_run("config", "--quiet", omit=(missing,))
    assert result.returncode != 0
    assert missing in result.stderr
    assert "synthetic-proxy-key" not in result.stderr + result.stdout
