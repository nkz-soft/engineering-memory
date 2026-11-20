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
    launch = [line for line in windows.splitlines() if 'Parameters: "setup --installer"' in line]
    assert len(launch) == 1
    assert 'Filename: "{app}\\engineering-memory.exe"' in launch[0]
    assert {"postinstall", "skipifsilent", "runasoriginaluser"} <= set(launch[0].split())
    assert "postinst" not in linux
