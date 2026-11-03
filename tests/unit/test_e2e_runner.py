"""An absent, skipped or spoofed end-to-end case cannot satisfy the gate."""

import xml.etree.ElementTree as ET

import pytest
from deploy.hindsight import e2e

CASE = "tests.integration.test_import_recall_e2e"
NAMES = [
    "test_import_and_recall",
    "test_import_to_access_tools",
    "test_pipeline_known_repository_and_tags",
    "test_wire_timestamp_omission_is_detected",
    "test_reimport_unchanged",
    "test_reimport_state_loss",
    "test_reimport_changed",
]


def report(names=NAMES, classname=CASE, outcome=None, coding=True):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for name in names:
        case = ET.SubElement(suite, "testcase", name=name, classname=classname)
        if outcome:
            ET.SubElement(case, outcome)
    if coding:
        case = ET.SubElement(
            suite,
            "testcase",
            name="test_cross_source_import_to_stdio",
            classname="tests.integration.test_coding_agent_access",
        )
        if outcome:
            ET.SubElement(case, outcome)
    return root


def test_complete_e2e_report_passes():
    e2e.verify_report(report())


@pytest.mark.parametrize("names", [[], NAMES[:-1], [*NAMES, NAMES[0]]])
def test_missing_or_duplicate_case_fails(names):
    with pytest.raises(ValueError, match="end-to-end"):
        e2e.verify_report(report(names))


def test_same_name_in_wrong_module_fails():
    with pytest.raises(ValueError, match="end-to-end"):
        e2e.verify_report(report(classname="unrelated"))


@pytest.mark.parametrize("outcome", ["skipped", "failure", "error"])
def test_nonpassing_case_fails(outcome):
    with pytest.raises(ValueError, match="end-to-end"):
        e2e.verify_report(report(outcome=outcome))


def test_gate_cleans_its_resources_even_when_worker_times_out(monkeypatch, tmp_path):
    import subprocess

    calls = []

    def timeout(command, ready):
        assert ready.name == "ready"
        calls.append(command)
        raise subprocess.TimeoutExpired(command, 1020)

    monkeypatch.setattr(e2e, "supervise", timeout)
    monkeypatch.setattr(e2e, "cleanup", lambda identity: calls.append(identity))
    with pytest.raises(subprocess.TimeoutExpired):
        e2e.main()
    assert calls[0][-2] == calls[1]


def test_gate_does_not_swallow_cleanup_failure(monkeypatch):
    monkeypatch.setattr(e2e, "supervise", lambda *a, **k: None)

    def fail(identity):
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(e2e, "cleanup", fail)
    with pytest.raises(RuntimeError, match="cleanup failed"):
        e2e.main()


def test_cleanup_has_one_total_deadline(monkeypatch):
    calls = []
    monkeypatch.setattr(e2e.subprocess, "run", lambda command, **kw: calls.append((command, kw)))
    e2e.cleanup("synthetic-run")
    assert calls[0][0][-2:] == ["--cleanup", "synthetic-run"]
    assert calls[0][1]["timeout"] == 90
    assert calls[0][1]["check"] is True


def test_cleanup_attempts_remaining_resources_after_remove_failure(monkeypatch):
    from unittest.mock import Mock

    client = Mock()
    failed, remaining, network = Mock(), Mock(), Mock()
    failed.remove.side_effect = RuntimeError("remove failed")
    client.containers.list.return_value = [failed, remaining]
    client.networks.list.return_value = [network]
    monkeypatch.setattr(e2e.docker, "from_env", lambda **kw: client)
    with pytest.raises(ExceptionGroup, match="cleanup"):
        e2e.cleanup_resources("synthetic-run")
    remaining.remove.assert_called_once_with(force=True, v=True)
    network.remove.assert_called_once_with()
    client.close.assert_called_once_with()
    assert client.containers.list.call_args.kwargs["filters"] == {
        "label": "engineering-memory.e2e-run=synthetic-run"
    }


def test_readiness_deadline_fails_closed():
    import time

    with pytest.raises(TimeoutError, match="readiness deadline"):
        e2e.wait_ready("http://127.0.0.1:1/health/ready", time.monotonic() - 1)


def test_supervisor_kills_startup_stalled_in_image_pull(monkeypatch, tmp_path):
    import subprocess
    from unittest.mock import Mock

    process = Mock()
    process.poll.return_value = None
    monkeypatch.setattr(e2e.subprocess, "Popen", lambda *a, **k: process)
    clock = iter([0, 601])
    monkeypatch.setattr(e2e.time, "monotonic", lambda: next(clock))
    with pytest.raises(subprocess.TimeoutExpired):
        e2e.supervise(["worker"], tmp_path / "ready")
    process.kill.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=15)


def test_supervisor_propagates_worker_failure(monkeypatch, tmp_path):
    import subprocess
    from unittest.mock import Mock

    process = Mock()
    process.poll.return_value = 17
    monkeypatch.setattr(e2e.subprocess, "Popen", lambda *a, **k: process)
    with pytest.raises(subprocess.CalledProcessError) as failed:
        e2e.supervise(["worker"], tmp_path / "ready")
    assert failed.value.returncode == 17
    process.kill.assert_not_called()


def test_supervisor_accepts_completed_ready_worker(monkeypatch, tmp_path):
    from unittest.mock import Mock

    process = Mock()
    process.poll.return_value = 0
    process.wait.return_value = 0
    ready = tmp_path / "ready"
    ready.touch()
    monkeypatch.setattr(e2e.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(e2e.time, "monotonic", lambda: 0)
    e2e.supervise(["worker"], ready)
    process.wait.assert_called_once_with(timeout=1020)
    process.kill.assert_not_called()


@pytest.mark.parametrize(
    "missing", ["test_reimport_unchanged", "test_reimport_state_loss", "test_reimport_changed"]
)
def test_each_reimport_case_is_required(missing):
    names = NAMES
    with pytest.raises(ValueError, match="end-to-end"):
        e2e.verify_report(report([name for name in names if name != missing]))


def test_cross_agent_case_cannot_be_omitted():
    with pytest.raises(ValueError, match="end-to-end"):
        e2e.verify_report(report(coding=False))
