"""Consumer configuration cannot configure the shared memory service (issue #48)."""

from __future__ import annotations

import os

import pytest

from engineering_memory.settings import SettingsError, load_settings

SERVICE = {
    "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL": "http://service:8088",
    "ENGINEERING_MEMORY_LLM__BASE_URL": "http://service:4000/v1",
}
CONSUMER = {
    "HERMES_HINDSIGHT__BASE_URL": "http://consumer:8088",
    "HERMES_LLM__BASE_URL": "http://consumer:4000/v1",
    "HERMES_LOGGING__LEVEL": "invalid-consumer-level",
    "HERMES_LOGGING__INCLUDE_CONVERSATION_CONTENT": "true",
}


@pytest.fixture(autouse=True)
def clean_namespaces(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.upper().startswith(("ENGINEERING_MEMORY_", "HERMES_")):
            monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("consumer_present", [False, True])
def test_service_environment_ignores_consumer_settings(monkeypatch, consumer_present) -> None:
    for name, value in SERVICE.items():
        monkeypatch.setenv(name, value)
    if consumer_present:
        for name, value in CONSUMER.items():
            monkeypatch.setenv(name, value)
    settings = load_settings(env_file=None)
    assert settings.hindsight.base_url.host == "service"
    assert settings.llm.base_url.host == "service"
    assert settings.logging.level == "INFO"
    assert settings.logging.include_conversation_content is False


@pytest.mark.parametrize("source", ["environment", "file"])
def test_consumer_only_values_cannot_satisfy_required_settings(
    monkeypatch, tmp_path, source
) -> None:
    values = {key: value for key, value in CONSUMER.items() if "BASE_URL" in key}
    path = None
    if source == "environment":
        for name, value in values.items():
            monkeypatch.setenv(name, value)
    else:
        path = tmp_path / ".env"
        path.write_text("\n".join(f"{key}={value}" for key, value in values.items()))
    with pytest.raises(SettingsError):
        load_settings(env_file=path)


def test_service_file_ignores_consumer_keys_and_environment_wins(monkeypatch, tmp_path) -> None:
    path = tmp_path / ".env"
    values = SERVICE | CONSUMER
    path.write_text("\n".join(f"{key}={value}" for key, value in values.items()))
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://override:4000/v1")
    settings = load_settings(env_file=path)
    assert settings.hindsight.base_url.host == "service"
    assert settings.llm.base_url.host == "override"
    assert settings.logging.level == "INFO"
    assert settings.logging.include_conversation_content is False
