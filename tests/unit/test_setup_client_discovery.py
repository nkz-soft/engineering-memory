import sys
from itertools import combinations
from pathlib import Path

import pytest

from engineering_memory import setup_client_discovery as discovery

WINDOWS = sys.platform == "win32"
CODEX_PACKAGE = "OpenAI.Codex_2p2nqsd0c76g0"
CLAUDE_PACKAGE = "Claude_pzs8sxrjxfjjc"
CLIENTS = ("codex-cli", "codex-desktop", "claude-code", "claude-desktop")
SUBSETS = [subset for n in range(5) for subset in combinations(CLIENTS, n)]


def create(path: Path, contents=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o700)


@pytest.fixture
def machine(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": str(tmp_path / "bin"),
        "LOCALAPPDATA": str(home / "Local"),
        "APPDATA": str(home / "Roaming"),
        "XDG_CONFIG_HOME": str(home / "xdg"),
        "PROGRAMDATA": str(tmp_path / "system/ProgramData"),
        "ProgramFiles": str(tmp_path / "system/Program Files"),
    }
    return home, tmp_path / "system", env, set()


def install(client, machine):
    _, root, env, packages = machine
    if client in {"codex-cli", "claude-code"}:
        name = "codex" if client == "codex-cli" else "claude"
        create(Path(env["PATH"]) / (name + (".exe" if WINDOWS else "")))
    elif WINDOWS:
        packages.add(CODEX_PACKAGE if client == "codex-desktop" else CLAUDE_PACKAGE)
    else:
        package = "chatgpt" if client == "codex-desktop" else "claude-desktop"
        create(root / "usr/bin" / package)
        create(root / "var/lib/dpkg/info" / (package + ".list"), f"/usr/bin/{package}\n")


def scan(machine, desktop_codex_home=None):
    home, root, env, packages = machine
    return discovery.discover(
        home=home,
        environment=env,
        system_root=root,
        windows_packages=lambda: packages,
        desktop_codex_home=desktop_codex_home,
    )


def packaged_claude(env, profile):
    return (
        Path(env["LOCALAPPDATA"])
        / f"Packages/{CLAUDE_PACKAGE}/LocalCache/Roaming/{profile}/claude_desktop_config.json"
    )


@pytest.mark.parametrize("installed", SUBSETS, ids=lambda items: "+".join(items) or "none")
def test_required_discovery_matrix(machine, installed):
    home, _, env, _ = machine
    for client in installed:
        install(client, machine)
    before = sorted(home.rglob("*"))
    expected = {
        "codex-cli": home / ".codex/config.toml",
        "codex-desktop": home / ".codex/config.toml",
        "claude-code": home / ".claude.json",
        "claude-desktop": packaged_claude(env, "Claude")
        if WINDOWS
        else Path(env["XDG_CONFIG_HOME"]) / "Claude/claude_desktop_config.json",
    }
    clients = scan(machine)
    assert {client.id: client.config for client in clients} == {
        client: expected[client] for client in installed
    }
    assert {
        target.config: {client.id for client in target.clients}
        for target in discovery.group_targets(clients)
    } == {
        path: {client for client in installed if expected[client] == path}
        for path in {expected[client] for client in installed}
    }
    assert sorted(home.rglob("*")) == before


def test_custom_profiles_can_be_shared_or_distinct(machine):
    home, _, env, _ = machine
    env["CODEX_HOME"] = str(home / "custom Codex")
    env["CLAUDE_CONFIG_DIR"] = str(home / "custom Claude")
    for client in CLIENTS:
        install(client, machine)
    for desktop_home, count in [(home / "custom Codex", 3), (home / "desktop Codex", 4)]:
        clients = scan(machine, desktop_home)
        configs = {client.id: client.config for client in clients}
        assert configs["codex-cli"] == home / "custom Codex/config.toml"
        assert configs["codex-desktop"] == desktop_home / "config.toml"
        assert configs["claude-code"] == home / "custom Claude/.claude.json"
        assert len(discovery.group_targets(clients)) == count


def test_ignores_residual_profiles_and_desktop_helpers(machine):
    home, root, env, packages = machine
    create(home / ".codex/config.toml")
    create(home / ".claude.json")
    create(home / ".claude/settings.json")
    create(Path(env["APPDATA"]) / "Claude/claude_desktop_config.json")
    create(root / "opt/claude-desktop/resources/claude")
    create(packaged_claude(env, "Claude-3p"))
    packages.add("Unrelated.Claude_fixture")
    assert scan(machine) == ()


@pytest.mark.skipif(not WINDOWS, reason="Windows package layouts")
def test_packaged_3p_takes_precedence_over_roaming_residue(machine):
    _, _, env, _ = machine
    install("claude-desktop", machine)
    create(Path(env["APPDATA"]) / "Claude/claude_desktop_config.json")
    create(packaged_claude(env, "Claude-3p"))
    assert scan(machine)[0].config == packaged_claude(env, "Claude-3p")
    create(packaged_claude(env, "Claude"))
    assert scan(machine)[0].config is None


@pytest.mark.skipif(not WINDOWS, reason="Windows npm and roaming layouts")
def test_npm_payload_and_unpacked_desktop(machine):
    home, _, env, _ = machine
    bin_dir = Path(env["PATH"])
    create(bin_dir / "codex.cmd")
    create(Path(env["LOCALAPPDATA"]) / "AnthropicClaude/Claude.exe")
    assert [client.id for client in scan(machine)] == ["claude-desktop"]
    vendor = bin_dir / "node_modules/@openai/codex/node_modules/@openai"
    create(vendor / "codex-win32-x64/vendor/x86_64-pc-windows-msvc/codex/codex.exe")
    assert {client.id: client.config for client in scan(machine)} == {
        "codex-cli": home / ".codex/config.toml",
        "claude-desktop": Path(env["APPDATA"]) / "Claude/claude_desktop_config.json",
    }


@pytest.mark.skipif(WINDOWS, reason="Ubuntu packaging")
def test_ubuntu_desktop_requires_vendor_package_evidence(machine):
    _, root, _, _ = machine
    create(root / "usr/bin/chatgpt")
    create(root / "usr/bin/claude-desktop")
    assert scan(machine) == ()


def test_managed_settings_surface_a_diagnostic_without_editing(machine):
    _, root, env, _ = machine
    env["PROGRAMDATA"] = str(root / "ProgramData")
    env["ProgramFiles"] = str(root / "Program Files")
    for client in ("codex-cli", "claude-code"):
        install(client, machine)
    codex_policy = "ProgramData/OpenAI/Codex" if WINDOWS else "etc/codex"
    claude_policy = "Program Files/ClaudeCode" if WINDOWS else "etc/claude-code"
    create(root / codex_policy / "requirements.toml", "mcp_servers = {}\n")
    create(root / claude_policy / "managed-mcp.json", '{"mcpServers":{}}')
    codex, claude = scan(machine)
    assert "managed" in codex.diagnostic
    assert "managed" in claude.diagnostic
    assert not codex.config.exists()
    assert not claude.config.exists()


@pytest.mark.skipif(not WINDOWS, reason="Windows package layouts")
def test_ambiguous_3p_profile_is_never_replaced_by_a_stale_file(machine):
    _, _, env, _ = machine
    install("claude-desktop", machine)
    standard = packaged_claude(env, "Claude")
    third_party = packaged_claude(env, "Claude-3p")
    create(standard)
    third_party.parent.mkdir(parents=True)
    assert scan(machine)[0].config is None


@pytest.mark.skipif(not WINDOWS, reason="Windows native installer layouts")
def test_windows_standalone_codex_is_discovered_before_path_refresh(machine):
    home, _, env, _ = machine
    binary = Path(env["LOCALAPPDATA"]) / "Programs/OpenAI/Codex/bin/codex.exe"
    create(binary)
    assert [(client.id, client.config) for client in scan(machine)] == [
        ("codex-cli", home / ".codex/config.toml")
    ]


@pytest.mark.skipif(not WINDOWS, reason="Windows desktop package inventory")
def test_unavailable_windows_inventory_cannot_fall_back_to_legacy_profile(machine):
    home, root, env, _ = machine
    create(Path(env["LOCALAPPDATA"]) / "AnthropicClaude/Claude.exe")
    result = discovery.discover(
        home=home, environment=env, system_root=root, windows_packages=lambda: None
    )
    assert "Could not query Windows packages" in result[0].diagnostic
    assert discovery.group_targets(result) == ()


@pytest.mark.skipif(not WINDOWS, reason="Windows packaged profile modes")
def test_windows_3p_profile_resolves_using_mode_or_migration_marker(machine):
    home, root, env, packages = machine
    install("claude-desktop", machine)
    standard = packaged_claude(env, "Claude")
    third_party = packaged_claude(env, "Claude-3p")
    create(standard.parent / ".user-data-left.claude_pzs8sxrjxfjjc")
    create(third_party)
    assert scan(machine)[0].config == third_party
    create(standard)
    result = discovery.discover(
        home=home,
        environment=env,
        system_root=root,
        windows_packages=lambda: packages,
        desktop_claude_mode="3p",
    )
    assert result[0].config == third_party
