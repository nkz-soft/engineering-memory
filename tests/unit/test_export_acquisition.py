import os
from datetime import UTC, datetime
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest

from engineering_memory.archive.export_blobs import LocalExportBlobs
from engineering_memory.ingestion.acquisition_source import (
    AcquisitionError,
    InboxExportSource,
    ManualExportSource,
)
from engineering_memory.ingestion.chatgpt_preflight import ExportLimits, validate_export


def archive(path, entries):
    with ZipFile(path, "w", compression=ZIP_STORED) as output:
        for name, content in entries:
            output.writestr(ZipInfo(name, (2025, 1, 2, 3, 4, 6)), content)


@pytest.mark.parametrize("mode", ["manual", "watcher"])
def test_sources_share_validated_snapshot_contract(tmp_path, mode):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    path = inbox / "export.zip"
    archive(path, [("conversations.json", "[]")])
    if mode == "manual":
        source = ManualExportSource(path)
    else:
        observation = tmp_path / "observations.json"
        (inbox / "transfer.zip.part").write_bytes(b"partial")
        assert list(InboxExportSource(inbox, observation).discover()) == []
        source = InboxExportSource(inbox, observation)
    (candidate,) = source.discover()
    store = LocalExportBlobs(tmp_path / "archive")
    with store.stage(candidate, max_bytes=1_000_000) as staged:
        evidence = validate_export(staged.path, zip_offset_minutes=0)
        assert evidence.produced_at == datetime(2025, 1, 2, 3, 4, 6, tzinfo=UTC)
        assert evidence.kind == "zip_member_estimate"
        published = store.publish(staged)
    assert published.read_bytes() == path.read_bytes()
    assert store.verified_path(published.stem) == published


@pytest.mark.parametrize(
    "entries",
    [
        [("conversations.json", "[{}] invalid")],
        [("conversations.json", "[{},]")],
        [("conversations-000.json", "[]"), ("conversations-002.json", "[]")],
        [("conversations-0.json", "[]"), ("conversations-000.json", "[]")],
        [("unrelated.json", "[]")],
    ],
)
def test_preflight_rejects_ambiguous_or_incomplete_members(tmp_path, entries):
    path = tmp_path / "bad.zip"
    archive(path, entries)
    with pytest.raises(AcquisitionError, match="invalid_export"):
        validate_export(path)


def test_preflight_checks_corruption_outside_conversation_members(tmp_path):
    path = tmp_path / "bad.zip"
    archive(path, [("conversations.json", "[]"), ("attachment.txt", "uniquepayload")])
    path.write_bytes(path.read_bytes().replace(b"uniquepayload", b"brokenpayload"))
    with pytest.raises(AcquisitionError, match="invalid_export"):
        validate_export(path)


def test_expansion_budget(tmp_path):
    path = tmp_path / "large.zip"
    archive(path, [("conversations.json", "[]"), ("attachment.txt", "12345")])
    with pytest.raises(AcquisitionError, match="export_limit"):
        validate_export(path, limits=ExportLimits(expanded_bytes=6))


def test_changed_input_is_rejected_before_publishing(tmp_path):
    path = tmp_path / "export.zip"
    archive(path, [("conversations.json", "[]")])
    (candidate,) = ManualExportSource(path).discover()
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
    store = LocalExportBlobs(tmp_path / "archive")
    with (
        pytest.raises(AcquisitionError, match="export_changed"),
        store.stage(candidate, max_bytes=1_000_000),
    ):
        pytest.fail("a changed candidate must not be staged")
    assert not list((tmp_path / "archive").rglob("*.zip"))


def test_embedded_utc_member_time_needs_no_offset(tmp_path):
    from struct import pack

    path = tmp_path / "utc.zip"
    stamp = datetime(2025, 1, 2, 3, 4, 6, tzinfo=UTC)
    with ZipFile(path, "w") as output:
        member = ZipInfo("conversations.json")
        member.extra = pack("<HHBi", 0x5455, 5, 1, int(stamp.timestamp()))
        output.writestr(member, "[]")
    evidence = validate_export(path)
    assert evidence.produced_at == stamp
    assert evidence.kind == "zip_member_estimate"


def test_oversized_conversation_stops_preflight(tmp_path):
    path = tmp_path / "oversized.zip"
    archive(path, [("conversations.json", '["' + "x" * 20 + '"]')])
    with pytest.raises(AcquisitionError, match="export_limit"):
        validate_export(path, limits=ExportLimits(record_chars=10))


def test_overlapping_checks_skip_then_release(tmp_path):
    from engineering_memory.ingestion.acquisition_lock import acquisition_lock

    path = tmp_path / "state.db"
    with acquisition_lock(path) as first:
        assert first
        with acquisition_lock(path) as second:
            assert not second
    with acquisition_lock(path) as later:
        assert later


def test_preflight_requires_end_of_deflate_stream(tmp_path):
    from struct import pack_into, unpack_from
    from zipfile import ZIP_DEFLATED

    path = tmp_path / "cut-stream.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as output:
        output.writestr("conversations.json", "[]")
        output.writestr("late.txt", "hello" * 500)
    with ZipFile(path) as output:
        member = output.getinfo("late.txt")
    data = bytearray(path.read_bytes())
    first_central = data.index(b"PK\x01\x02")
    last_central = data.index(b"PK\x01\x02", first_central + 4)
    assert unpack_from("<I", data, last_central + 20)[0] == member.compress_size
    for header_offset in (member.header_offset + 18, last_central + 20):
        pack_into("<I", data, header_offset, member.compress_size - 1)
    path.write_bytes(data)
    with pytest.raises(AcquisitionError, match="invalid_export"):
        validate_export(path)


def test_valid_zip64_directory_and_large_deflated_member(tmp_path, monkeypatch):
    import zipfile

    path = tmp_path / "zip64.zip"
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 100)
    with ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr("conversations-000.json", "[]")
        output.writestr("conversations-001.json", "[]")
        output.writestr("attachment.txt", b"x" * (3 * 1024 * 1024))
    assert validate_export(path).produced_at is None


def test_preflight_rejects_non_json_constants(tmp_path):
    path = tmp_path / "invalid-json.zip"
    archive(path, [("conversations.json", '[{"invalid":NaN}]')])
    with pytest.raises(AcquisitionError, match="invalid_export"):
        validate_export(path)


def test_truncated_archive_comment_is_rejected(tmp_path):
    path = tmp_path / "truncated-comment.zip"
    with ZipFile(path, "w") as output:
        output.writestr("conversations.json", "[]")
        output.comment = b"synthetic comment"
    path.write_bytes(path.read_bytes()[:-5])
    with pytest.raises(AcquisitionError, match="invalid_export"):
        validate_export(path)


def test_local_crc_must_match_the_central_record(tmp_path):
    path = tmp_path / "bad-local-crc.zip"
    archive(path, [("conversations.json", "[]")])
    data = bytearray(path.read_bytes())
    data[14] ^= 1
    path.write_bytes(data)
    with pytest.raises(AcquisitionError, match="invalid_export"):
        validate_export(path)


@pytest.mark.parametrize("zip64", [False, True])
def test_streaming_zip_data_descriptor_is_verified(tmp_path, zip64):
    from io import BytesIO
    from zipfile import ZIP_DEFLATED

    class Unseekable(BytesIO):
        def seek(self, *args):
            raise OSError("not seekable")

    stream = Unseekable()
    with (
        ZipFile(stream, "w", compression=ZIP_DEFLATED) as output,
        output.open("conversations.json", "w", force_zip64=zip64) as member,
    ):
        member.write(b"[]")
    path = tmp_path / "stream.zip"
    data = stream.getvalue()
    path.write_bytes(data)
    assert validate_export(path).produced_at is None
    crc = data.index(b"PK\x07\x08") + 4
    path.write_bytes(data[:crc] + bytes([data[crc] ^ 1]) + data[crc + 1 :])
    with pytest.raises(AcquisitionError, match="invalid_export"):
        validate_export(path)
