from types import SimpleNamespace

from engineering_memory import setup_history


def test_discovery_finds_nested_agent_files_and_local_exports(tmp_path, monkeypatch):
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    inbox = tmp_path / "exports"
    history = codex / "sessions" / "2026" / "11" / "rollout.jsonl"
    history.parent.mkdir(parents=True)
    history.write_text("{}", encoding="utf-8")
    inbox.mkdir()
    export = inbox / "conversations.json"
    export.write_text('[{"id":"chatgpt-id","mapping":{}}]', encoding="utf-8")
    (inbox / "irrelevant.json").write_text('{"unrelated":true}', encoding="utf-8")
    claude_export = inbox / "claude.json"
    claude_export.write_text('[{"uuid":"claude-id","chat_messages":[]}]', encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(codex))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    assert {(entry.source, entry.path) for entry in setup_history.discover(inbox)} == {
        ("codex", history),
        ("chatgpt", export),
        ("claude-chat", claude_export),
    }


def test_failed_selected_source_does_not_block_later_sources(tmp_path, monkeypatch, capsys):
    paths = [tmp_path / name for name in ("bad.jsonl", "valid.jsonl", "declined.jsonl")]
    for path in paths:
        path.touch()
    candidates = [setup_history.Candidate("codex", path) for path in paths]
    monkeypatch.setattr(setup_history, "discover", lambda inbox: candidates)
    monkeypatch.setattr(
        setup_history, "load_settings", lambda: SimpleNamespace(chatgpt_export_inbox=None)
    )
    answers = iter([False, True, True, False, True])
    monkeypatch.setattr(setup_history.typer, "confirm", lambda *a, **kw: next(answers))
    called = []

    def run(data, path, force, version, *, source):
        called.append(path)
        if path == str(paths[0]):
            raise OSError("private exception contents")
        return SimpleNamespace(
            status="success", imported=1, skipped=0, failed=0, terminal_error=None
        )

    monkeypatch.setattr(setup_history, "run_import", run)
    assert not setup_history.import_selected()
    assert called == [str(p) for p in paths[:2]]
    output = capsys.readouterr().out
    assert "private exception contents" not in output
    assert "imported 1" in output


def test_selected_chatgpt_zip_uses_only_the_selected_source(tmp_path, monkeypatch):
    path = tmp_path / "chosen.zip"
    candidate = setup_history.Candidate("chatgpt", path)
    calls = []

    def run(data, selected, force, version, *, source):
        calls.append((selected, source))
        return SimpleNamespace(imported=1, skipped=0, failed=0, terminal_error=None)

    monkeypatch.setattr(setup_history, "run_import", run)
    assert setup_history._import_candidate(candidate, "test")
    assert calls == [(str(path), "chatgpt")]
