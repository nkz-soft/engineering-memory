"""Archive behavior at the real filesystem boundary; payloads are synthetic."""

from pathlib import Path

import pytest

from engineering_memory.archive import ArchiveDocumentNotFound, OriginalPayload
from tests.contracts import conversations


def local(root: Path):
    import importlib.util

    name = "engineering_memory.archive.local"
    assert importlib.util.find_spec(name) is not None, "local archive implementation is missing"
    from engineering_memory.archive.local import LocalRawArchive

    return LocalRawArchive(root)


@pytest.mark.parametrize("content", [b"", b"\x00\xff\xfe\x80", "Кириллица 🚀".encode()])
def test_binary_original_and_all_normalized_fields_survive_reopening(tmp_path, content):
    root = tmp_path / "archive"
    enriched = conversations.enrich(conversations.conversation_using_every_field())
    original = OriginalPayload(content=content, media_type="application/octet-stream")
    local(root).store(enriched, original)
    assert local(root).load(enriched.document_id) == enriched
    assert local(root).load_original(enriched.document_id) == original


def test_reads_and_construction_do_not_create_a_root(tmp_path):
    root = tmp_path / "absent"
    archive = local(root)
    assert list(archive.iter_document_ids()) == []
    with pytest.raises(ArchiveDocumentNotFound):
        archive.load("chatgpt:unknown")
    assert not root.exists()


@pytest.mark.parametrize("identifier", ["../outside", "a/b:c", "CON", "ёж:🧠", "a\\b", "a:b"])
def test_opaque_identifiers_do_not_select_filesystem_paths(tmp_path, identifier):
    enriched = conversations.enrich(conversations.conversation(identifier))
    archive = local(tmp_path / "root")
    archive.store(enriched, OriginalPayload(content=b"original", media_type="text/plain"))
    assert archive.load(enriched.document_id) == enriched
    assert list(archive.iter_document_ids()) == [enriched.document_id]
    assert {p.name for p in tmp_path.iterdir()} == {"root"}
    assert len(list((tmp_path / "root" / "v1").glob("*.json"))) == 1


def test_unpublished_replacement_preserves_the_previous_pair(tmp_path, monkeypatch):
    from engineering_memory.archive import ArchiveUnavailable

    archive = local(tmp_path)
    first = conversations.enrich(conversations.conversation(text="old"))
    archive.store(first, OriginalPayload(content=b"old", media_type="text/plain"))
    import engineering_memory.archive.local as implementation

    def fail(*args):
        raise OSError("private-canary")

    monkeypatch.setattr(implementation, "_publish", fail)
    with pytest.raises(ArchiveUnavailable) as raised:
        archive.store(
            conversations.enrich(conversations.conversation(text="new")),
            OriginalPayload(content=b"new", media_type="text/plain"),
        )
    assert "private-canary" not in str(raised.value)
    assert archive.load(first.document_id) == first
    assert archive.load_original(first.document_id).content == b"old"
    assert len(list((tmp_path / "v1").iterdir())) == 1


@pytest.mark.parametrize(
    "mutation",
    ["json", "version", "missing", "extra", "base64", "hash", "identity", "original_hash", "model"],
)
def test_corrupt_records_are_rejected_without_payload_diagnostics(tmp_path, mutation):
    import json

    from engineering_memory.archive import ArchiveRejected

    archive = local(tmp_path)
    enriched = conversations.enrich(conversations.conversation())
    archive.store(enriched, OriginalPayload(content=b"private-canary", media_type="text/plain"))
    path = next((tmp_path / "v1").glob("*.json"))
    record = json.loads(path.read_bytes())
    if mutation == "json":
        path.write_text("{private-canary")
    else:
        if mutation == "version":
            record["format_version"] = 2
        if mutation == "missing":
            del record["original"]
        if mutation == "extra":
            record["future"] = "private-canary"
        if mutation == "base64":
            record["original"]["content_base64"] = "!private-canary"
        if mutation == "hash":
            record["content_hash"] = "bad"
        if mutation == "identity":
            record["document_id"] = "chatgpt:different"
        if mutation == "original_hash":
            record["original"]["sha256"] = "bad"
        if mutation == "model":
            record["enriched"]["conversation"]["messages"][0]["role"] = "private-canary"
        path.write_text(json.dumps(record))
    for operation in (
        lambda: archive.load(enriched.document_id),
        lambda: archive.load_original(enriched.document_id),
        lambda: next(archive.iter_document_ids()),
    ):
        with pytest.raises(ArchiveRejected) as raised:
            operation()
        assert "private-canary" not in str(raised.value)
        assert not raised.value.retryable


def test_listing_continues_after_a_corrupt_entry_and_ignores_temporary_files(tmp_path):
    from engineering_memory.archive import ArchiveRejected

    archive = local(tmp_path)
    good = conversations.enrich(conversations.conversation())
    archive.store(good, OriginalPayload(content=b"ok", media_type="text/plain"))
    (tmp_path / "v1" / "bad.json").write_text("not a record")
    (tmp_path / "v1" / ".abandoned.tmp").write_bytes(b"not committed")
    reader = archive.iter_document_ids()
    ids, errors = [], []
    while True:
        try:
            ids.append(next(reader))
        except ArchiveRejected as error:
            errors.append(error)
        except StopIteration:
            break
    assert ids == ["chatgpt:abc123"]
    assert len(errors) == 1


def test_directory_and_read_failures_are_declared(tmp_path, monkeypatch):
    import engineering_memory.archive.local as implementation
    from engineering_memory.archive import ArchiveUnavailable

    archive = local(tmp_path)
    enriched = conversations.enrich(conversations.conversation())
    archive.store(enriched, OriginalPayload(content=b"ok", media_type="text/plain"))

    def fail(*args, **kwargs):
        raise PermissionError("private-canary")

    monkeypatch.setattr(implementation.os, "scandir", fail)
    with pytest.raises(ArchiveUnavailable) as raised:
        next(archive.iter_document_ids())
    assert "private-canary" not in str(raised.value)
    monkeypatch.setattr(implementation, "_read_bytes", fail)
    with pytest.raises(ArchiveUnavailable):
        archive.load(enriched.document_id)


def test_file_sync_failure_cannot_publish_a_replacement(tmp_path, monkeypatch):
    import engineering_memory.archive.local as implementation
    from engineering_memory.archive import ArchiveUnavailable

    archive = local(tmp_path)
    first = conversations.enrich(conversations.conversation(text="old"))
    archive.store(first, OriginalPayload(content=b"old", media_type="text/plain"))

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(implementation.os, "fsync", fail)
    with pytest.raises(ArchiveUnavailable):
        archive.store(
            conversations.enrich(conversations.conversation(text="new")),
            OriginalPayload(content=b"new", media_type="text/plain"),
        )
    assert archive.load(first.document_id) == first


@pytest.mark.parametrize("kind", ["version", "record"])
def test_redirected_storage_is_rejected(tmp_path, kind):
    from engineering_memory.archive import ArchiveRejected

    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    archive = local(root)
    item = conversations.enrich(conversations.conversation())
    payload = OriginalPayload(content=b"old", media_type="text/plain")
    archive.store(item, payload)
    record = next((root / "v1").glob("*.json"))
    target = root / "v1" if kind == "version" else record
    destination = outside if kind == "version" else outside / "private.json"
    if kind == "record":
        destination.write_bytes(record.read_bytes())
    if kind == "version":
        record.unlink()
        target.rmdir()
    else:
        target.unlink()
    try:
        target.symlink_to(destination, target_is_directory=kind == "version")
    except OSError:
        pytest.skip("creating symbolic links requires platform permission")
    with pytest.raises(ArchiveRejected):
        archive.load(item.document_id)
    with pytest.raises(ArchiveRejected):
        archive.store(item, payload)
    with pytest.raises(ArchiveRejected):
        list(archive.iter_document_ids())


def test_concurrent_readers_only_see_complete_committed_records(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    archive = local(tmp_path)
    first = conversations.enrich(conversations.conversation(text="old"))
    second = conversations.enrich(conversations.conversation(text="new"))
    archive.store(first, OriginalPayload(content=b"old", media_type="text/plain"))
    barrier = Barrier(2)

    def read():
        reader = local(tmp_path)
        barrier.wait()
        for _ in range(100):
            assert reader.load(first.document_id) in (first, second)
            assert reader.load_original(first.document_id).content in (b"old", b"new")

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(read)
        barrier.wait()
        for i in range(30):
            archive.store(
                second if i % 2 else first,
                OriginalPayload(content=b"new" if i % 2 else b"old", media_type="text/plain"),
            )
        future.result()


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows junction behavior")
def test_version_directory_junction_cannot_redirect_storage(tmp_path):
    import subprocess

    from engineering_memory.archive import ArchiveRejected

    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(root / "v1"), str(outside)],
        check=True,
        capture_output=True,
    )
    archive = local(root)
    item = conversations.enrich(conversations.conversation())
    with pytest.raises(ArchiveRejected):
        archive.store(item, OriginalPayload(content=b"private", media_type="text/plain"))
    with pytest.raises(ArchiveRejected):
        archive.load(item.document_id)
    with pytest.raises(ArchiveRejected):
        list(archive.iter_document_ids())
    assert list(outside.iterdir()) == []


def test_identity_listing_is_lazy_and_a_terminal_listing_error_ends_iteration(
    tmp_path, monkeypatch
):
    import engineering_memory.archive.local as implementation
    from engineering_memory.archive import ArchiveUnavailable

    archive = local(tmp_path)
    calls = []

    def fail(*args):
        calls.append(True)
        raise PermissionError("unavailable")

    monkeypatch.setattr(implementation.os, "scandir", fail)
    iterator = archive.iter_document_ids()
    assert calls == []
    with pytest.raises(ArchiveUnavailable):
        next(iterator)
    with pytest.raises(StopIteration):
        next(iterator)
    assert calls == [True]


def test_post_publication_sync_failure_reports_failure_but_leaves_complete_new_pair(
    tmp_path, monkeypatch
):
    import engineering_memory.archive.local as implementation
    from engineering_memory.archive import ArchiveUnavailable

    archive = local(tmp_path)
    first = conversations.enrich(conversations.conversation(text="old"))
    second = conversations.enrich(conversations.conversation(text="new"))
    archive.store(first, OriginalPayload(content=b"old", media_type="text/plain"))

    def fail(*args):
        raise OSError("directory sync failed")

    monkeypatch.setattr(implementation, "_sync_directory", fail)
    with pytest.raises(ArchiveUnavailable):
        archive.store(second, OriginalPayload(content=b"new", media_type="text/plain"))
    assert archive.load(second.document_id) == second
    assert archive.load_original(second.document_id).content == b"new"


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows sharing behavior")
def test_windows_publication_retries_transient_sharing_failures(tmp_path, monkeypatch):
    import ctypes

    import engineering_memory.archive._windows as windows

    archive = local(tmp_path)
    first = conversations.enrich(conversations.conversation(text="old"))
    second = conversations.enrich(conversations.conversation(text="new"))
    archive.store(first, OriginalPayload(content=b"old", media_type="text/plain"))
    real_move = windows._move
    attempts = []

    def contended(*args):
        attempts.append(True)
        if len(attempts) <= 2:
            ctypes.set_last_error(5 if len(attempts) == 1 else 32)
            return 0
        return real_move(*args)

    monkeypatch.setattr(windows, "_move", contended)
    archive.store(second, OriginalPayload(content=b"new", media_type="text/plain"))
    assert archive.load(second.document_id) == second
    assert archive.load_original(second.document_id).content == b"new"


@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_format_version_does_not_coerce_other_types_to_integer_one(tmp_path, version):
    import json

    from engineering_memory.archive import ArchiveRejected

    archive = local(tmp_path)
    item = conversations.enrich(conversations.conversation())
    archive.store(item, OriginalPayload(content=b"ok", media_type="text/plain"))
    path = next((tmp_path / "v1").glob("*.json"))
    value = json.loads(path.read_bytes())
    value["format_version"] = version
    path.write_text(json.dumps(value))
    with pytest.raises(ArchiveRejected):
        archive.load(item.document_id)


def test_invalid_root_listing_failure_is_terminal(tmp_path):
    from engineering_memory.archive import ArchiveUnavailable

    root = tmp_path / "not-a-directory"
    root.write_text("blocked")
    reader = local(root).iter_document_ids()
    with pytest.raises(ArchiveUnavailable):
        next(reader)
    with pytest.raises(StopIteration):
        next(reader)


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows extended paths")
def test_windows_parent_components_in_configured_root_round_trip(tmp_path):
    (tmp_path / "child").mkdir()
    root = tmp_path / "child" / ".." / "archive"
    item = conversations.enrich(conversations.conversation())
    payload = OriginalPayload(content=b"original", media_type="text/plain")
    local(root).store(item, payload)
    assert local(root).load(item.document_id) == item
    assert local(root).load_original(item.document_id) == payload
    assert list(local(root).iter_document_ids()) == ["chatgpt:abc123"]
