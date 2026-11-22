import json
import stat

import pytest

from engineering_memory import setup_clients as setup
from engineering_memory.setup_client_discovery import Client, Target


@pytest.fixture(params=("codex-desktop", "claude-desktop", "claude-code"))
def target(request, tmp_path):
    client = request.param
    path = (
        tmp_path / "custom profile" / ("config.toml" if client == "codex-desktop" else "mcp.json")
    )
    return Target(path, (Client(client, client, path),))


def seed(target, text):
    target.config.parent.mkdir(parents=True, exist_ok=True)
    target.config.write_bytes(text.encode())


def test_registration_creates_only_selected_absolute_stdio(target, tmp_path):
    executable = tmp_path / "Установленные программы/engineering-memory.exe"
    state = setup.inspect(target, executable)
    assert state.state == "absent"
    assert not target.config.exists()
    assert setup.persist(state, executable).state == "saved"
    saved = target.config.read_bytes()
    assert setup.inspect(target, executable).state == "matching"
    assert (
        setup.persist(setup.inspect(target, executable), executable).state == "already configured"
    )
    assert target.config.read_bytes() == saved


def test_codex_conflict_preserves_other_settings_and_requires_confirmation(tmp_path):
    config = tmp_path / "config.toml"
    target = Target(config, (Client("codex-cli", "Codex CLI", config),))
    executable = tmp_path / "installed.exe"
    before = (
        '# profile\r\nservice_tier = "default"  # keep\r\n'
        '[mcp_servers."engineering-memory"]\r\ncommand = "uv"\r\nargs = ["run", "serve"]\r\n'
        '[mcp_servers.other]\r\ncommand = "another tool"\r\n'
    )
    seed(target, before)
    state = setup.inspect(target, executable)
    assert state.state == "conflict"
    assert "service_tier" in state.diagnostic
    assert setup.persist(state, executable).state == "declined"
    assert config.read_bytes() == before.encode()
    assert setup.persist(state, executable, replace=True).state == "saved"
    assert setup.inspect(target, executable).state == "matching"
    after = config.read_bytes()
    assert b'# profile\r\nservice_tier = "default"  # keep\r\n' in after
    assert b'[mcp_servers.other]\r\ncommand = "another tool"\r\n' in after


@pytest.mark.parametrize(
    "prefix", ["mcp_servers.engineering-memory.", 'mcp_servers."engineering-memory".']
)
def test_codex_dotted_mcp_entry_can_be_replaced(tmp_path, prefix):
    config = tmp_path / "config.toml"
    target = Target(config, (Client("codex-desktop", "Codex Desktop", config),))
    executable = tmp_path / "installed"
    seed(target, f'{prefix}command = "uv"\n{prefix}args = ["serve"]\n')
    state = setup.inspect(target, executable)
    assert setup.persist(state, executable, replace=True).state == "saved"
    assert setup.inspect(target, executable).state == "matching"


def test_json_edit_keeps_foreign_entries_and_values(tmp_path):
    config = tmp_path / "claude.json"
    target = Target(config, (Client("claude-code", "Claude Code", config),))
    executable = tmp_path / "installed"
    source = {
        "account": {"x": "fixture"},
        "mcpServers": {"other": {"command": "foreign"}, "engineering-memory": None},
    }
    seed(target, json.dumps(source))
    state = setup.inspect(target, executable)
    assert state.state == "conflict"
    assert setup.persist(state, executable, replace=True).state == "saved"
    current = json.loads(config.read_text(encoding="utf-8"))
    entry = current["mcpServers"].pop("engineering-memory")
    assert entry["command"] == str(executable)
    assert entry["args"] == ["serve"]
    source["mcpServers"].pop("engineering-memory")
    assert current == source


def test_stale_consent_cannot_replace_a_changed_file(target, tmp_path):
    executable = tmp_path / "installed"
    if target.config.suffix == ".toml":
        entry = '[mcp_servers.engineering-memory]\ncommand = "old"\n'
        modified = entry.replace('"old"', '"new"')
    else:
        entry = '{"mcpServers":{"engineering-memory":{"command":"old"}}}'
        modified = entry.replace('"old"', '"new"')
    seed(target, entry)
    stale = setup.inspect(target, executable)
    seed(target, modified)
    assert setup.persist(stale, executable, replace=True).state == "blocked"
    assert target.config.read_bytes() == modified.encode()


def test_failed_publication_leaves_previous_entry(target, tmp_path, monkeypatch):
    executable = tmp_path / "installed"
    old = (
        '[mcp_servers.engineering-memory]\ncommand = "old"\n'
        if target.config.suffix == ".toml"
        else '{"mcpServers":{"engineering-memory":{"command":"old"}}}'
    )
    seed(target, old)

    def fail(*args, **kwargs):
        raise OSError("fixture secret")

    monkeypatch.setattr(setup, "_publish", fail)
    result = setup.persist(setup.inspect(target, executable), executable, replace=True)
    assert result.state == "failed"
    assert "fixture secret" not in result.diagnostic
    assert target.config.read_bytes() == old.encode()


@pytest.mark.parametrize(
    "text", ['{"mcpServers":{},"mcpServers":{}}', '{"mcpServers":[]}', '{"bad":NaN}']
)
def test_malformed_json_blocks_setup(tmp_path, text):
    config = tmp_path / "config.json"
    target = Target(config, (Client("claude-code", "Claude Code", config),))
    seed(target, text)
    executable = tmp_path / "installed"
    assert setup.inspect(target, executable).state == "blocked"
    assert config.read_bytes() == text.encode()


def test_nonregular_target_blocks_setup(target, tmp_path):
    target.config.mkdir(parents=True)
    assert setup.inspect(target, tmp_path / "installed").state == "blocked"


def test_changes_during_staging_preserve_external_write(target, tmp_path, monkeypatch):
    executable = tmp_path / "installed"
    old, new = (
        ("model = 'old'\n", "model = 'new'\n")
        if target.config.suffix == ".toml"
        else ('{"model":"old"}', '{"model":"new"}')
    )
    seed(target, old)
    original = setup.tempfile.NamedTemporaryFile

    def change(*args, **kwargs):
        seed(target, new)
        return original(*args, **kwargs)

    state = setup.inspect(target, executable)
    monkeypatch.setattr(setup.tempfile, "NamedTemporaryFile", change)
    assert setup.persist(state, executable).state == "blocked"
    assert target.config.read_bytes() == new.encode()


def test_existing_permissions_are_preserved_on_posix(target, tmp_path):
    if setup.os.name == "nt":
        pytest.skip("POSIX permissions")
    executable = tmp_path / "installed"
    seed(target, "" if target.config.suffix == ".toml" else "{}")
    target.config.chmod(0o640)
    assert setup.persist(setup.inspect(target, executable), executable).state == "saved"
    assert stat.S_IMODE(target.config.stat().st_mode) == 0o640


def test_multiple_dotted_codex_registrations_stay_at_the_same_scope(tmp_path):
    import tomllib

    config = tmp_path / "config.toml"
    target = Target(config, (Client("codex-cli", "Codex CLI", config),))
    executable = tmp_path / "installed"
    before = (
        'mcp_servers.one.command = "one" # keep one\nmcp_servers.two.command = "two" # keep two\n'
    )
    seed(target, before)
    assert setup.persist(setup.inspect(target, executable), executable).state == "saved"
    after = config.read_bytes().decode()
    other = tomllib.loads(after)["mcp_servers"]
    other.pop("engineering-memory")
    assert other == tomllib.loads(before)["mcp_servers"]
    assert before in after


def test_json_edit_does_not_round_unrelated_configuration(tmp_path):
    config = tmp_path / "config.json"
    target = Target(config, (Client("claude-desktop", "Claude Desktop", config),))
    executable = tmp_path / "installed"
    new = "0.1234567890123456789"
    seed(target, '{"setting": ' + new + ', "mcpServers": {"other":{"command":"foreign"}}}')
    assert setup.persist(setup.inspect(target, executable), executable).state == "saved"
    assert new in config.read_bytes().decode()
