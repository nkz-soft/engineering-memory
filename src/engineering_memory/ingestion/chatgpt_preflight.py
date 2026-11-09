"""Validate the full staged ZIP before the conversation pipeline is allowed to run."""

import json
import zipfile
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from io import TextIOWrapper
from pathlib import Path
from struct import calcsize, unpack_from
from typing import BinaryIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile, ZipInfo

from engineering_memory.ingestion.acquisition_source import AcquisitionError
from engineering_memory.ingestion.acquisition_state import EvidenceKind
from engineering_memory.ingestion.chatgpt.export import _SPLIT, SINGLE, _conversation_files
from engineering_memory.ingestion.chatgpt.records import RecordScanner, RecordTooLarge
from engineering_memory.ingestion.source import SourceFormatError, SourceUnavailable

_CHUNK = 1024 * 1024
_SIZE_IN_ZIP64 = 0xFFFFFFFF
_HAS_DESCRIPTOR = 0x08


@dataclass(frozen=True)
class ExportLimits:
    compressed_bytes: int = 4 * 1024**3
    expanded_bytes: int = 16 * 1024**3
    member_count: int = 100_000
    directory_bytes: int = 64 * 1024**2
    record_chars: int = 32 * 1024**2


DEFAULT_LIMITS = ExportLimits()


@dataclass(frozen=True)
class ProductionEvidence:
    produced_at: datetime | None = None
    kind: EvidenceKind = "unknown"


def validate_export(
    path: Path,
    *,
    limits: ExportLimits = DEFAULT_LIMITS,
    zip_offset_minutes: int | None = None,
) -> ProductionEvidence:
    try:
        if path.stat().st_size > limits.compressed_bytes:
            raise AcquisitionError("export_limit")
        with path.open("rb") as raw:
            _check_directory(raw, limits)
            return _validate_members(raw, limits, zip_offset_minutes)
    except RecordTooLarge:
        raise AcquisitionError("export_limit") from None
    except (BadZipFile, EOFError, ValueError, RuntimeError, SourceFormatError, zlib.error):
        raise AcquisitionError("invalid_export") from None
    except (OSError, SourceUnavailable):
        raise AcquisitionError("archive_unavailable") from None


def _validate_members(
    raw: BinaryIO, limits: ExportLimits, zip_offset_minutes: int | None
) -> ProductionEvidence:
    with ZipFile(raw) as export:
        members = export.infolist()
        names = export.namelist()
        if len(set(names)) != len(names):
            raise AcquisitionError("invalid_export")
        conversations = _conversation_files(names)
        if conversations != (SINGLE,):
            indices = [int(_SPLIT.fullmatch(name)[1]) for name in conversations]
            if indices != list(range(len(indices))):
                raise AcquisitionError("invalid_export")
        if sum(info.file_size for info in members) > limits.expanded_bytes:
            raise AcquisitionError("export_limit")
        for info in members:
            # zipfile checks the local header, flags, filename and member boundaries.
            with export.open(info):
                pass
            _check_payload(raw, info)
        decoder = json.JSONDecoder(parse_constant=_reject_constant)
        for name in conversations:
            with TextIOWrapper(export.open(name), encoding="utf-8", newline="") as stream:
                for _ in RecordScanner(
                    stream,
                    raw_decode=decoder.raw_decode,
                    allow_trailing_comma=False,
                    max_record_chars=limits.record_chars,
                ):
                    pass
        return _production_evidence(
            [export.getinfo(name) for name in conversations], zip_offset_minutes
        )


def _reject_constant(_: str) -> None:
    raise ValueError("not a JSON constant")


def _check_directory(raw: BinaryIO, limits: ExportLimits) -> None:
    # Read the same end record as Python's ZipFile, including ZIP64, then bound
    # and count entries before ZipFile builds its index.
    end = zipfile._EndRecData(raw)
    if (
        end is None
        or end[zipfile._ECD_DISK_NUMBER]
        or end[zipfile._ECD_DISK_START]
        or end[zipfile._ECD_ENTRIES_THIS_DISK] != end[zipfile._ECD_ENTRIES_TOTAL]
        or len(end[zipfile._ECD_COMMENT]) != end[zipfile._ECD_COMMENT_SIZE]
    ):
        raise AcquisitionError("invalid_export")
    count = end[zipfile._ECD_ENTRIES_TOTAL]
    start, size = end[zipfile._ECD_OFFSET], end[zipfile._ECD_SIZE]
    if size > limits.directory_bytes or count > limits.member_count:
        raise AcquisitionError("export_limit")
    location = end[zipfile._ECD_LOCATION]
    # Older Python 3.13 releases return the original EOCD position for ZIP64.
    if end[zipfile._ECD_SIGNATURE] == zipfile.stringEndArchive64:
        zip64_trailer_size = zipfile.sizeEndCentDir64 + zipfile.sizeEndCentDir64Locator
        if location - (start + size) == zip64_trailer_size:
            raw.seek(start + size)
            if raw.read(4) == zipfile.stringEndArchive64:
                location -= zip64_trailer_size
    if start + size != location:
        raise AcquisitionError("invalid_export")
    raw.seek(start)
    entries = 0
    while raw.tell() < start + size:
        header = raw.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise AcquisitionError("invalid_export")
        entries += 1
        if entries > limits.member_count:
            raise AcquisitionError("export_limit")
        raw.seek(sum(unpack_from("<HHH", header, 28)), 1)
    if raw.tell() != start + size or entries != count:
        raise AcquisitionError("invalid_export")


def _check_payload(raw: BinaryIO, info: ZipInfo) -> None:
    if info.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
        raise AcquisitionError("invalid_export")

    # ZipExtFile can emit all expected bytes before noticing a missing end of
    # the compressed stream. Read the declared compressed range directly.
    raw.seek(info.header_offset + 6)
    flags, method, _, _, crc, compressed_size, file_size, name_size, extra_size = unpack_from(
        "<HHHHIIIHH", raw.read(24)
    )
    if flags != info.flag_bits or method != info.compress_type:
        raise AcquisitionError("invalid_export")
    if not flags & _HAS_DESCRIPTOR and (
        crc != info.CRC
        or compressed_size not in (info.compress_size, _SIZE_IN_ZIP64)
        or file_size not in (info.file_size, _SIZE_IN_ZIP64)
    ):
        raise AcquisitionError("invalid_export")
    raw.seek(name_size + extra_size, 1)
    inflater = zlib.decompressobj(-zlib.MAX_WBITS) if info.compress_type == ZIP_DEFLATED else None
    remaining, count, crc = info.compress_size, 0, 0
    while remaining:
        compressed = raw.read(min(remaining, _CHUNK))
        if not compressed:
            raise AcquisitionError("invalid_export")
        remaining -= len(compressed)
        while compressed:
            if inflater is None:
                output, compressed = compressed, b""
            else:
                output = inflater.decompress(compressed, min(_CHUNK, info.file_size - count + 1))
                compressed = inflater.unconsumed_tail
                if inflater.unused_data:
                    raise AcquisitionError("invalid_export")
            count += len(output)
            if count > info.file_size:
                raise AcquisitionError("invalid_export")
            crc = zlib.crc32(output, crc)
    if (inflater is not None and not inflater.eof) or count != info.file_size or crc != info.CRC:
        raise AcquisitionError("invalid_export")
    if flags & _HAS_DESCRIPTOR:
        zip64 = (
            _SIZE_IN_ZIP64 in (compressed_size, file_size)
            or max(info.compress_size, info.file_size) >= _SIZE_IN_ZIP64
        )
        _check_descriptor(raw, info, zip64=zip64)


def _check_descriptor(raw: BinaryIO, info: ZipInfo, *, zip64: bool) -> None:
    layout = "<IQQ" if zip64 else "<III"
    size = calcsize(layout)
    data = raw.read(min(size + 4, info._end_offset - raw.tell()))
    expected = (info.CRC, info.compress_size, info.file_size)
    if len(data) >= size and unpack_from(layout, data) == expected:
        return
    if (
        len(data) == size + 4
        and data[:4] == b"PK\x07\x08"
        and unpack_from(layout, data, 4) == expected
    ):
        return
    raise AcquisitionError("invalid_export")


def _production_evidence(members: list[ZipInfo], offset_minutes: int | None) -> ProductionEvidence:
    try:
        times = [_member_time(member, offset_minutes) for member in members]
    except (ValueError, OverflowError, OSError):
        return ProductionEvidence()
    if any(value is None for value in times):
        return ProductionEvidence()
    newest, oldest = max(times), min(times)
    if (
        newest > datetime.now(UTC) + timedelta(minutes=5)
        or oldest.year < 2022
        or newest - oldest > timedelta(days=1)
    ):
        return ProductionEvidence()
    return ProductionEvidence(newest, "zip_member_estimate")


def _member_time(member: ZipInfo, offset_minutes: int | None) -> datetime | None:
    # Info-ZIP's central-directory UT extra field holds a UTC modification time.
    offset = 0
    extra = member.extra
    times = set()
    while offset + 4 <= len(extra):
        tag, length = unpack_from("<HH", extra, offset)
        start = offset + 4
        offset = start + length
        if offset > len(extra):
            return None
        if tag == 0x5455 and length >= 5 and extra[start] & 1:
            times.add(unpack_from("<i", extra, start + 1)[0])
    if len(times) == 1:
        return datetime.fromtimestamp(times.pop(), UTC)
    if times or offset_minutes is None:
        return None
    zone = timezone(timedelta(minutes=offset_minutes))
    return datetime(*member.date_time, tzinfo=zone).astimezone(UTC)
