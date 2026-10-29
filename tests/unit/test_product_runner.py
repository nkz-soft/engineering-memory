"""Lifecycle failures must not become successful tests or destructive global cleanup."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy/product/run.py"


@pytest.fixture
def runner():
    assert SCRIPT.is_file(), "bounded product runner is missing"
    spec = importlib.util.spec_from_file_location("product_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def env():
    return {
        "PRODUCT_PROXY_KEY": "synthetic-secret",
        "PRODUCT_PROVIDER_MODEL": "openai/synthetic",
        "PRODUCT_PROVIDER_API_BASE": "https://example.invalid/v1",
        "PRODUCT_PROVIDER_API_KEY": "synthetic-key",
    }


def test_identity_is_unique_and_cleanup_rejects_foreign_projects(runner):
    first, second = runner.RunIdentity.create(), runner.RunIdentity.create()
    assert first.project != second.project
    assert first.bank == first.project
    assert first.cleanup_project(first.project) == first.project
    for name in ("engineering-memory-product-dev", second.project, "em-e2e-foreign", "--all"):
        with pytest.raises(runner.DeploymentError):
            first.cleanup_project(name)


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_deadlines_are_positive_and_finite(runner, value):
    with pytest.raises(runner.DeploymentError):
        runner.Limits(startup=value)


def test_preflight_names_missing_variable_without_value(runner, env):
    env.pop("PRODUCT_PROVIDER_MODEL")
    with pytest.raises(runner.DeploymentError) as error:
        runner.validate_environment(env, external=False)
    assert "PRODUCT_PROVIDER_MODEL" in str(error.value)
    assert "synthetic-secret" not in str(error.value)


def test_external_proxy_does_not_require_internal_provider(runner):
    runner.validate_environment(
        {
            "PRODUCT_PROXY_KEY": "synthetic",
            "PRODUCT_PROXY_URL": "http://host.docker.internal:4000/v1",
        },
        external=True,
    )
    with pytest.raises(runner.DeploymentError):
        runner.validate_environment(
            {"PRODUCT_PROXY_KEY": "synthetic", "PRODUCT_PROXY_URL": "http://localhost:4000"},
            external=True,
        )


@pytest.mark.parametrize("fail_at", ["startup", "provision", "scenario", "cleanup", None])
def test_e2e_failure_and_cleanup_are_scoped(runner, env, fail_at):
    calls = []

    def execute(args, *, env, timeout):
        assert timeout > 0
        calls.append(args)
        stage = (
            "cleanup"
            if "down" in args
            else (
                "startup"
                if "up" in args
                else ("provision" if args[-1] == "provision" else "scenario")
            )
        )
        if fail_at == stage:
            raise runner.DeploymentError(stage + " failed")

    report = runner.run_e2e(env, execute=execute, ready=True)
    assert report.code == (0 if fail_at is None else 1)
    assert "down" in calls[-1]
    assert "--volumes" in calls[-1]
    projects = {args[args.index("-p") + 1] for args in calls}
    assert len(projects) == 1
    assert next(iter(projects)).startswith("em-e2e-")
    if fail_at == "provision":
        assert not any(args[-1] == "e2e" for args in calls)
    assert "synthetic-secret" not in report.message


@pytest.mark.parametrize("failure", [KeyboardInterrupt(), subprocess.TimeoutExpired(["secret"], 1)])
def test_interruption_still_cleans_own_resources(runner, env, failure):
    calls = []

    def execute(args, **kwargs):
        calls.append(args)
        if "up" in args:
            raise failure

    report = runner.run_e2e(env, execute=execute, ready=True)
    assert report.code != 0
    assert "down" in calls[-1]
    assert "secret" not in report.message


def test_unavailable_live_e2e_is_visible_skip_before_docker(runner, env):
    def forbidden(*args, **kwargs):
        pytest.fail("live prerequisite skip must not create resources")

    report = runner.run_e2e(env, execute=forbidden, ready=False)
    assert report.code == 77
    assert "SKIPPED" in report.message


def test_subprocess_failure_never_echoes_payload(runner, monkeypatch):
    def failed(*args, **kwargs):
        assert kwargs["stdout"] == subprocess.DEVNULL
        assert kwargs["stderr"] == subprocess.DEVNULL
        return subprocess.CompletedProcess(args[0], 9)

    monkeypatch.setattr(runner.subprocess, "run", failed)
    with pytest.raises(runner.DeploymentError) as error:
        runner.execute(["docker", "secret"], env={}, timeout=1)
    assert "secret" not in str(error.value)


def test_cli_skip_is_non_success_without_opt_in():
    assert SCRIPT.exists(), "runner is missing"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "e2e"], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 77
    assert "SKIPPED" in result.stdout


def test_runtime_storage_directories_are_owned_by_application():
    text = (ROOT / "Dockerfile").read_text()
    assert "mkdir -p /var/lib/engineering-memory/archive" in text
    assert "chown -R engineering-memory:engineering-memory /var/lib/engineering-memory" in text


def test_missing_credential_set_skips_live_without_creation(runner):
    def forbidden(*args, **kwargs):
        pytest.fail("missing credentials must not create resources")

    report = runner.run_e2e({}, ready=True, execute=forbidden)
    assert report.code == 77
    assert "credentials" in report.message


def test_alias_cannot_diverge_from_internal_proxy(runner, env):
    env["PRODUCT_MODEL_ALIAS"] = "wrong-route"
    with pytest.raises(runner.DeploymentError, match="PRODUCT_MODEL_ALIAS"):
        runner.validate_environment(env, external=False)


def test_total_deadline_includes_startup_and_provision(runner, env, monkeypatch):
    clock = [0]
    monkeypatch.setattr(runner.time, "monotonic", lambda: clock[0])
    calls = []

    def execute(args, **kwargs):
        calls.append(args)
        clock[0] += 10

    report = runner.run_e2e(env, ready=True, execute=execute, limits=runner.Limits(total=5))
    assert report.code == 1
    assert len(calls) == 2  # startup exhausted total budget, then owned cleanup
    assert "down" in calls[-1]


def test_safe_cli_error_identifies_missing_variable(runner, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runner.os, "environ", {})
    result = runner.main(["dependencies", "--env-file", str(tmp_path / "missing")])
    assert result == 1
    assert "PRODUCT_PROXY_KEY" in capsys.readouterr().err


def test_cli_live_with_missing_credentials_is_skip_when_ready(
    runner, tmp_path, monkeypatch, capsys
):
    manifest = tmp_path / "capabilities.json"
    manifest.write_text('{"ready":true}')
    monkeypatch.setattr(runner, "HERE", tmp_path)
    monkeypatch.setattr(runner.os, "environ", {})
    result = runner.main(["e2e", "--live", "--env-file", str(tmp_path / "absent")])
    assert result == 77
    assert "credentials" in capsys.readouterr().out


def test_stop_works_after_credentials_are_cleared(runner, tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text("PRODUCT_PROXY_KEY=\nPRODUCT_PROXY_URL=\n")
    monkeypatch.setattr(runner.os, "environ", {})
    calls = []

    def execute(args, *, env, timeout):
        calls.append(args)
        assert env["PRODUCT_PROXY_KEY"].strip()
        assert env["PRODUCT_PROXY_URL"].strip()

    monkeypatch.setattr(runner, "execute", execute)
    assert runner.main(["stop", "--external", "--env-file", str(envfile)]) == 0
    assert "down" in calls[0]
