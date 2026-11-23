import tomllib
from pathlib import Path

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
