import hashlib
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_first_release_version_matches_lockfile():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    packages = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))["package"]
    locked = next(package for package in packages if package["name"] == project["name"])
    assert project["version"] == locked["version"] == "0.0.1"


def test_release_workflow_separates_build_and_draft_permissions():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert {target["os"] for target in jobs["build"]["strategy"]["matrix"]["include"]} == {
        "windows-2025",
        "ubuntu-24.04",
    }
    build_steps = {step["name"]: step for step in jobs["build"]["steps"] if "name" in step}
    handoff = build_steps["Verify Ubuntu installer handoff"]
    names = list(build_steps)
    assert names.index("Verify Ubuntu installer handoff") > names.index("Generate package checksum")
    assert 'script --quiet --return --command "bash' in handoff["run"]
    assert "packaging/workstation/smoke.py /usr/bin/engineering-memory" in handoff["run"]
    draft = jobs["draft"]
    assert draft["needs"] == "build"
    assert draft["permissions"] == {"contents": "write"}
    script = "\n".join(step.get("run", "") for step in draft["steps"])
    assert "sha256sum -c" in script
    assert "gh release create" in script and "--draft" in script
    assert 'assets=("$windows" "$linux" "$launcher")' in script
    assert '"${release_files[@]}"' in script
    assert "ubuntu-amd64-install.sh" in script


@pytest.mark.parametrize(
    ("sidecar_format", "valid"),
    [
        ("{digest}  {name}\n", True),
        ("{digest} *{name}\n", True),
        ("{digest} !{name}\n", False),
        ("{digest}  other.exe\n", False),
        ("{wrong_digest} *{name}\n", False),
        ("{digest} *{name}\n{digest} *{name}\n", False),
    ],
    ids=["text", "binary", "invalid-mode", "wrong-file", "wrong-hash", "multiple-lines"],
)
def test_draft_checks_release_assets(tmp_path, sidecar_format, valid):
    bash = shutil.which("bash")
    git = shutil.which("git")
    if os.name == "nt" and git:
        git_bash = Path(git).resolve().parents[1] / "bin/bash.exe"
        if git_bash.is_file():
            bash = str(git_bash)
    if not bash:
        pytest.skip("Bash is required to run the release verification script")

    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    draft = next(step["run"] for step in workflow["jobs"]["draft"]["steps"] if "run" in step)
    verify_assets, publish, _ = draft.partition('if gh release view "$TAG"')
    assert publish

    assets = tmp_path / "assets"
    assets.mkdir()
    names = (
        "engineering-memory-0.0.1-windows-x64-setup.exe",
        "engineering-memory_0.0.1_amd64.deb",
        "engineering-memory-0.0.1-ubuntu-amd64-install.sh",
    )
    for name in names:
        payload = name.encode()
        (assets / name).write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        pattern = sidecar_format if name.endswith(".exe") else "{digest}  {name}\n"
        (assets / f"{name}.sha256").write_bytes(
            pattern.format(digest=digest, wrong_digest="0" * 64, name=name).encode()
        )

    script = tmp_path / "verify-assets.sh"
    script.write_bytes(verify_assets.encode())
    result = subprocess.run(
        [bash, script.name],
        cwd=tmp_path,
        env={**os.environ, "TAG": "v0.0.1"},
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (result.returncode == 0) == valid, result.stdout + result.stderr


def test_workstation_compose_is_loopback_only_and_keeps_backend_volume():
    config = yaml.safe_load((ROOT / "deploy/workstation/compose.yaml").read_text(encoding="utf-8"))
    assert config["services"]["hindsight"]["extends"]["file"] == "../hindsight/service.yaml"
    assert "hindsight-data" in config["volumes"]
    for service in config["services"].values():
        for port in service.get("ports", []):
            assert port.startswith("127.0.0.1:")
    assert "build:" not in str(config)


def test_package_scripts_declare_architecture_and_runtime_metadata():
    directory = ROOT / "packaging/workstation"
    windows = (directory / "windows.iss").read_text(encoding="utf-8")
    linux = (directory / "build-deb.sh").read_text(encoding="utf-8")
    build = (directory / "build.py").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in windows
    assert "ArchitecturesAllowed=x64compatible" in windows
    assert "Architecture: amd64" in linux
    assert "--copy-metadata" in build
    assert "tag must match" in build


def test_interactive_install_offers_setup_in_current_user_session():
    directory = ROOT / "packaging/workstation"
    windows = (directory / "windows.iss").read_text(encoding="utf-8")
    linux = (directory / "build-deb.sh").read_text(encoding="utf-8")
    assert "CreateCustomPage(wpInstalling" in windows
    assert "WizardSilent" in windows
    assert "IsAdmin" in windows
    assert "PasswordChar := " in windows
    assert "ExecAndCaptureOutput" in windows
    assert "[Run]" not in windows
    assert "StartPage.Values[0] := False" in windows
    assert "if not StartPage.Values[0] then" in windows
    assert "EM_INSTALLER_UI_" in windows
    assert "postinst" not in linux


def test_windows_release_smoke_covers_both_silent_modes_and_profile_preservation():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    build = workflow["jobs"]["build"]["steps"]
    smoke = next(
        step["run"] for step in build if "smoke-test Windows installer" in step.get("name", "")
    )
    assert all(flag in smoke for flag in ("'/SILENT'", "'/VERYSILENT'", "'/LOG="))
    assert "Silent install created a workstation profile" in smoke
    assert "Silent reinstall changed the workstation profile" in smoke


def test_workstation_proxy_overlay_routes_only_litellm_and_keeps_hindsight_direct():
    path = "deploy/workstation/compose.proxy.yaml"
    overlay = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    assert set(overlay["services"]) == {"hindsight", "litellm"}
    settings = overlay["services"]["litellm"]["environment"]
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY"):
        assert settings[name] == settings[name.lower()]
    for name in ("localhost", "127.0.0.1", "::1", "hindsight", "litellm"):
        assert name in settings["NO_PROXY"]
    direct = overlay["services"]["hindsight"]["environment"]
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        assert direct[name] == direct[name.lower()] == ""
    assert path in (ROOT / "packaging/workstation/build.py").read_text(encoding="utf-8")


def test_identical_run_guards_all_persistent_installation_actions():
    windows = (ROOT / "packaging/workstation/windows.iss").read_text(encoding="utf-8")
    assert "Uninstallable=ShouldInstallPayload" in windows
    assert "CreateUninstallRegKey=ShouldInstallPayload" in windows
    assert "Check: ShouldInstallPayload" in windows
    assert "if (CurStep = ssPostInstall) and ShouldInstallPayload" in windows


def test_existing_configuration_defers_mutation_until_final_confirmation():
    windows = (ROOT / "packaging/workstation/windows.iss").read_text(encoding="utf-8")
    assert "if ConfigureExisting then" in windows
    assert "ConfirmMaintenanceChanges" in windows
    assert "SaveMaintenanceSettings" in windows
