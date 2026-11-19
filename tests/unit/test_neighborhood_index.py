"""Exercise the SQLite projection with synthesized classified records."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import perf_counter
from types import SimpleNamespace

import pytest
from sqlalchemy import event

from engineering_memory.archive import ArchiveRejected, ArchiveUnavailable


class SyntheticArchive:
    def __init__(self, records):
        self.records = records

    def iter_document_ids(self):
        return iter(self.records)

    def load(self, document_id):
        record = self.records[document_id]
        if isinstance(record, Exception):
            raise record
        return record


@pytest.fixture
def graph(tmp_path, monkeypatch):
    from engineering_memory.access import neighborhood_index as module
    from engineering_memory.access.neighborhood_evidence import EvidenceEdge, Node

    monkeypatch.setattr(module, "project_of", lambda archived: archived.project)
    monkeypatch.setattr(module, "project_evidence", lambda archived: iter(archived.edges))

    def record(number, *, project="alpha", relations=()):
        document_id = f"codex:{number:05d}"
        origin = Node("session", document_id, document_id)
        edges = [
            EvidenceEdge(
                project,
                origin,
                target,
                relation,
                document_id,
                message,
                None,
                "content",
                timestamp,
                "guard",
            )
            for message, (relation, target, timestamp) in enumerate(relations)
        ]
        return SimpleNamespace(document_id=document_id, project=project, edges=edges)

    path = tmp_path / "state" / "neighborhood.sqlite"
    return SimpleNamespace(
        path=path,
        index=module.NeighborhoodIndex(path),
        Node=Node,
        record=record,
        IndexUnavailable=module.IndexUnavailable,
    )


def archive(*records):
    return SyntheticArchive({record.document_id: record for record in records})


OLD = "2026-01-01T00:00:00.000000+00:00"
NEW = "2026-06-01T00:00:00.000000+00:00"


def test_unbuilt_index_is_read_only_and_empty(graph):
    assert graph.index.neighborhood("alpha", graph.Node("session", "x", "x")) == {
        "status": "unindexed",
        "edges": [],
        "truncated": False,
    }
    assert graph.index.evidence("alpha", "x") is None
    assert not graph.path.exists()


def test_redirected_index_storage_is_unavailable(graph, monkeypatch):
    file = graph.Node("file", "a.py", "a.py", "owner/one")
    graph.index.rebuild(archive())
    wal = graph.path.with_name(graph.path.name + "-wal")
    monkeypatch.setattr(Path, "is_junction", lambda path: path == wal)

    with pytest.raises(graph.IndexUnavailable):
        graph.index.neighborhood("alpha", file)
    with pytest.raises(graph.IndexUnavailable):
        graph.index.rebuild(archive())


def test_only_latest_edit_by_exact_project_and_repository_is_returned(graph):
    file = graph.Node("file", "src/shared.py", "shared.py", "owner/one")
    other_repo = graph.Node("file", "src/shared.py", "shared.py", "owner/two")
    first = graph.record(1, relations=[("file_edit", file, NEW), ("file_edit", file, OLD)])
    second = graph.record(2, relations=[("file_edit", other_repo, NEW)])
    third = graph.record(3, project="beta", relations=[("file_edit", file, NEW)])
    coverage = graph.index.rebuild(archive(first, second, third))
    reverse = graph.index.neighborhood("alpha", file)
    forward = graph.index.neighborhood("alpha", first.edges[0].origin)

    assert reverse["status"] == "ready"
    assert reverse["coverage"] == coverage
    assert coverage["indexed"] == 3
    [edge] = reverse["edges"]
    assert forward["edges"] == [edge]
    assert edge["origin"]["identity"] == "codex:00001"
    assert edge["target"]["repository"] == "owner/one"
    assert edge["relation"] == "file_edit"
    assert graph.index.evidence("alpha", edge["handle"]) == first.edges[0]
    assert graph.index.evidence("beta", edge["handle"]) is None


def test_continuation_requires_an_exact_same_project_archive_record(graph):
    targets = [graph.Node("session", f"codex:{n:05d}", f"Session {n}") for n in range(2, 5)]
    origin = graph.record(1, relations=[("continuation", target, OLD) for target in targets])
    graph.index.rebuild(archive(origin, graph.record(2), graph.record(3, project="beta")))

    [edge] = graph.index.neighborhood("alpha", origin.edges[0].origin)["edges"]
    assert edge["target"]["identity"] == "codex:00002"
    assert graph.index.neighborhood("alpha", targets[0])["edges"] == [edge]


def test_partial_refresh_can_skip_invalid_listing_entries_and_unavailable_records(graph):
    root = graph.Node("session", "codex:00001", "Session 1")

    class PartialArchive(SyntheticArchive):
        def iter_document_ids(self):
            ids = iter(self.records)

            class Listing:
                rejected = False

                def __next__(self):
                    if not self.rejected:
                        self.rejected = True
                        raise ArchiveRejected("corrupt listing entry")
                    return next(ids)

            return Listing()

    partial = PartialArchive(
        {
            "codex:00001": graph.record(1),
            "codex:00002": ArchiveUnavailable("unavailable record"),
            "codex:00003": graph.record(3, project=None),
        }
    )
    graph.index.rebuild(partial)
    result = graph.index.neighborhood("alpha", root)
    assert result["status"] == "partial"
    assert result["edges"] == []
    assert result["coverage"]["indexed"] == 1
    assert result["coverage"]["skipped"] == 2


def test_failed_and_parallel_rebuild_keep_the_published_generation(graph):
    file = graph.Node("file", "src/shared.py", "shared.py", "owner/one")
    first = graph.record(1, relations=[("file_edit", file, OLD)])
    second = graph.record(2, relations=[("file_edit", file, NEW)])
    graph.index.rebuild(archive(first))
    visible = graph.index.neighborhood("alpha", file)
    [edge] = visible["edges"]

    waiting, release = Event(), Event()

    class InterruptedArchive(SyntheticArchive):
        def iter_document_ids(self):
            yield second.document_id
            waiting.set()
            if not release.wait(10):
                raise AssertionError("the reader and competing writer did not finish")
            raise ArchiveUnavailable("listing terminated")

    with ThreadPoolExecutor(max_workers=1) as executor:
        build = executor.submit(
            graph.index.rebuild, InterruptedArchive({second.document_id: second})
        )
        try:
            assert waiting.wait(10)
            assert graph.index.neighborhood("alpha", file) == visible
            with pytest.raises(graph.IndexUnavailable):
                type(graph.index)(graph.path).rebuild(archive(second))
        finally:
            release.set()
        with pytest.raises(graph.IndexUnavailable):
            build.result(timeout=10)
    assert graph.index.neighborhood("alpha", file) == visible
    assert graph.index.evidence("alpha", edge["handle"]) == first.edges[0]

    graph.index.rebuild(archive(first))
    assert graph.index.evidence("alpha", edge["handle"]) is None
    assert len(graph.index.neighborhood("alpha", file)["edges"]) == 1


def test_busy_root_lookup_is_bounded_and_index_ordered(graph, record_property):
    file = graph.Node("file", "src/shared.py", "shared.py", "owner/one")

    class LargeArchive:
        def iter_document_ids(self):
            return (f"codex:{number:05d}" for number in range(50_000))

        def load(self, document_id):
            number = int(document_id.split(":")[-1])
            target = (
                file
                if number < 2_500
                else graph.Node(
                    "file",
                    f"src/{number}.py",
                    f"{number}.py",
                    "owner/one",
                )
            )
            return graph.record(
                number, relations=[("file_edit", target, NEW if number == 2499 else OLD)]
            )

    assert graph.index.rebuild(LargeArchive())["indexed"] == 50_000
    start = perf_counter()
    first = graph.index.neighborhood("alpha", file)
    record_property("busy_file_lookup_seconds", perf_counter() - start)
    plans = []

    @event.listens_for(graph.index._reader, "before_cursor_execute")
    def inspect_adjacency(connection, cursor, statement, parameters, context, executemany):
        if not context.execution_options.get("explain") and "ORDER BY" in statement:
            assert "LIMIT" in statement and parameters[-2:] == (31, 0)
            plan = connection.exec_driver_sql(
                f"EXPLAIN QUERY PLAN {statement}",
                parameters,
                execution_options={"explain": True},
            )
            plans.append([row[-1] for row in plan])

    assert first == graph.index.neighborhood("alpha", file)
    assert first["truncated"] is True
    assert [edge["origin"]["identity"] for edge in first["edges"]] == [
        "codex:02499",
        *(f"codex:{number:05d}" for number in range(29)),
    ]
    assert len(plans) == 2
    for plan in plans:
        assert len(plan) == 1
        assert "SEARCH" in plan[0] and "USING INDEX" in plan[0]


@pytest.mark.parametrize("redirect_after", [0, 1, 2])
def test_rejected_archive_listing_preserves_previous_local_generation(
    tmp_path, monkeypatch, redirect_after
):
    from engineering_memory.access.neighborhood_evidence import Node
    from engineering_memory.access.neighborhood_index import IndexUnavailable, NeighborhoodIndex
    from engineering_memory.archive import OriginalPayload
    from engineering_memory.archive.local import LocalRawArchive
    from engineering_memory.normalization import Source
    from tests.unit.test_deep_recall import record

    archive_root = tmp_path / "archive"
    archive = LocalRawArchive(archive_root)
    index = NeighborhoodIndex(tmp_path / "index.sqlite3")
    item = record(Source.CODEX, "one", "See https://github.com/example/demo/pull/1")
    archive.store(item, OriginalPayload(content=b"recorded", media_type="text/plain"))
    index.rebuild(archive)
    root = Node("session", "codex:one", "codex:one")
    before = index.neighborhood("demo", root)

    checks = iter([False] * redirect_after + [True])
    monkeypatch.setattr(
        Path, "is_junction", lambda path: path == archive_root / "v1" and next(checks, True)
    )
    with pytest.raises(IndexUnavailable):
        index.rebuild(archive)
    assert index.neighborhood("demo", root) == before


def test_refresh_creates_private_index_and_archive_root(tmp_path, monkeypatch):
    import os
    from stat import S_IMODE

    from engineering_memory.access.neighborhood_index import NeighborhoodIndex

    directory = tmp_path / "private"
    path = directory / "neighborhood.sqlite3"
    open_file = os.open
    mkdir = Path.mkdir
    modes = {}

    def observe_open(name, flags, mode=0o777, **options):
        if Path(name) == path:
            modes["index"] = mode
        return open_file(name, flags, mode, **options)

    def observe_mkdir(target, mode=0o777, *args, **options):
        if target == directory:
            modes["directory"] = mode
        return mkdir(target, mode, *args, **options)

    monkeypatch.setattr(os, "open", observe_open)
    monkeypatch.setattr(Path, "mkdir", observe_mkdir)
    NeighborhoodIndex(path).rebuild(archive())
    assert modes == {"index": 0o600, "directory": 0o700}
    if os.name == "posix":
        assert S_IMODE(directory.stat().st_mode) == 0o700
        assert S_IMODE(path.stat().st_mode) == 0o600
