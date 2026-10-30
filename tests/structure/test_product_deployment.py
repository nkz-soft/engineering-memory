"""Effective product configuration, validated without contacting a provider."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy/product"


def render(*overlays, project="em-e2e-synthetic"):
    if not shutil.which("docker"):
        pytest.skip("Compose configuration validation requires the Docker CLI, no daemon needed")
    version = subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=10)
    if version.returncode:
        pytest.skip("Docker Compose plugin is not installed")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PRODUCT_", "HINDSIGHT_"))}
    env.update(
        PRODUCT_PROXY_URL="http://proxy.invalid:4000/v1",
        PRODUCT_PROXY_KEY="synthetic-proxy",
        PRODUCT_PROVIDER_MODEL="openai/synthetic",
        PRODUCT_PROVIDER_API_KEY="synthetic-provider",
        PRODUCT_PROVIDER_API_BASE="https://example.invalid/v1",
    )
    args = [
        "docker",
        "compose",
        "--env-file",
        os.devnull,
        "-p",
        project,
        "-f",
        str(DEPLOY / "compose.yaml"),
    ]
    for name in overlays:
        args += ["-f", str(DEPLOY / name)]
    result = subprocess.run(
        [*args, "--profile", "internal", "--profile", "tools", "config", "--format", "json"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_product_compose_exists():
    assert (DEPLOY / "compose.yaml").is_file(), "product orchestration is missing"


def test_engine_configuration_is_reused_with_private_e2e_resources():
    config = render("compose.e2e.yaml")
    engine = config["services"]["hindsight"]
    assert "@sha256:" in engine["image"]
    assert engine["healthcheck"]["retries"] > 0
    assert engine["shm_size"] == "1gb" or engine["shm_size"] == "1073741824"
    for service in config["services"].values():
        assert not service.get("ports")
        assert "container_name" not in service
    for volume in config["volumes"].values():
        assert volume["name"].startswith("em-e2e-synthetic_")
        assert not volume.get("external")
    for role in ("app", "provision", "import", "status", "mcp", "e2e"):
        env = config["services"][role]["environment"]
        assert env["ENGINEERING_MEMORY_HINDSIGHT__BANK_ID"] == "em-e2e-synthetic"
        assert env["ENGINEERING_MEMORY_ARCHIVE_ROOT"].startswith("/var/lib/")
    assert (
        config["services"]["import"]["depends_on"]["provision"]["condition"]
        == "service_completed_successfully"
    )
    assert not config["services"]["mcp"].get("tty", False)


def test_development_and_external_proxy_keep_persistence_and_loopback():
    config = render("compose.dev.yaml", project="engineering-memory-product-dev")
    assert config["services"]["hindsight"]["ports"][0]["host_ip"] == "127.0.0.1"
    app = config["services"]["app"]
    assert app["build"]["context"] == str(ROOT)
    assert len(app["volumes"]) == 2
    assert app["environment"]["ENGINEERING_MEMORY_HINDSIGHT__BANK_ID"] == "engineering-global"
    external = render("compose.external.yaml")
    assert not external["services"]["hindsight"].get("depends_on")
    assert "litellm" not in external["services"]


def test_missing_product_prerequisites_are_explicit():
    manifest = json.loads((DEPLOY / "capabilities.json").read_text())
    assert manifest["ready"] is False
    assert set(manifest["blocked_by"]) >= {"17", "21", "23", "24"}


def test_build_context_excludes_operator_secrets():
    patterns = (ROOT / ".dockerignore").read_text().splitlines()
    assert "**/.env" in patterns
    assert "**/.env.*" in patterns


def test_all_product_roles_share_one_repository_image():
    config = render("compose.e2e.yaml")
    images = {
        config["services"][role].get("image")
        for role in ("app", "provision", "import", "status", "mcp", "e2e")
    }
    assert images == {"em-e2e-synthetic-app:local"}


def test_host_endpoints_work_for_all_consumers_on_linux():
    config = render("compose.dev.yaml")
    for role in ("hindsight", "litellm", "app"):
        assert "host.docker.internal=host-gateway" in config["services"][role]["extra_hosts"]
