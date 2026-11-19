"""Recognize explicit neighborhood relations in sanitized archive records."""

import json
import re
import shlex
from bisect import bisect_left
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC
from hashlib import sha256

from engineering_memory.access.handoff import (
    _CODEX_EXIT,
    _affirms_edit,
    _object,
    _result_success,
)
from engineering_memory.normalization import EnrichedConversation, ProjectTag, Role, Source

FILE_EDIT = "file_edit"
COMMIT = "commit"
PR_REFERENCE = "pr_reference"
CONTINUATION = "continuation"

_MAX_FIELD = 256 * 1024
_MAX_IDENTITY = 1024
_CLAUDE_EDITS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
_DRIVE = re.compile(r"^[a-zA-Z]:/")
_UNSAFE_SHELL = re.compile(r"[\r\n;&|<>()$%\x60]")
_OID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
_COMMIT_RESULT = re.compile(r"\A\[[^\]\r\n]+ ([0-9a-fA-F]{7,64})\](?: |\r?\n|\Z)")
_PATCH_PATH = re.compile(r"(?m)^\*\*\* (?:Add File|Delete File|Update File|Move to): (.+)\r?$")
_PR = re.compile(
    r"(?i)(?<![\w/:])https://([a-z0-9]+(?:[.-][a-z0-9]+)+)/"
    r"([a-z0-9_.-]+)/([a-z0-9_.-]+)/(pull/[1-9][0-9]{0,17})"
    r"(?![\w/%-])"
)
_SOURCE_NAMES = "|".join(source.value for source in Source)
_CONTINUATION = re.compile(
    rf"\A[ \t]*(?i:continue from|continuation of|resume from)(?i: session)?[ \t]+"
    rf"(?:\x60((?:{_SOURCE_NAMES}):[a-zA-Z0-9_.:-]+)\x60|"
    rf"((?:{_SOURCE_NAMES}):[a-zA-Z0-9_.:-]+?))(?=\.?(?:\s|\Z))"
)


@dataclass(frozen=True, slots=True)
class Node:
    kind: str
    identity: str
    label: str
    repository: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceEdge:
    project: str
    origin: Node
    target: Node
    relation: str
    document_id: str
    message: int
    tool: int | None
    field: str
    observed_at: str
    snapshot: str


@dataclass(frozen=True, slots=True)
class _ToolField:
    message: int
    tool: int
    name: str
    payload: dict


@dataclass(frozen=True, slots=True)
class _AbsolutePath:
    anchor: str
    parts: tuple[str, ...]

    def relative_to(self, root: "_AbsolutePath") -> tuple[str, ...] | None:
        length = len(root.parts)
        if self.anchor == root.anchor and self.parts[:length] == root.parts:
            return self.parts[length:]
        return None


def project_of(archived: EnrichedConversation) -> str | None:
    conversation, provenance = archived.conversation, archived.provenance
    project = provenance.project
    if (
        project not in (None, "unknown", "unclassified")
        and conversation.source == provenance.source
        and conversation.source_id == provenance.source_id
        and any(isinstance(tag, ProjectTag) and tag.value == project for tag in archived.tags)
    ):
        return project
    return None


def snapshot_of(archived: EnrichedConversation) -> str:
    """Bind positional selectors to content, times and the exact recorded scope."""
    conversation, provenance = archived.conversation, archived.provenance
    scope = (
        archived.document_id,
        provenance.source,
        provenance.source_id,
        provenance.project,
        tuple(str(tag) for tag in archived.tags if isinstance(tag, ProjectTag)),
        conversation.repository,
        provenance.repository,
        conversation.working_directory,
        conversation.started_at.isoformat(),
        conversation.last_activity_at.isoformat() if conversation.last_activity_at else None,
    )
    digest = sha256(json.dumps(scope, ensure_ascii=True).encode())
    for message in conversation.messages:
        digest.update(b"\n")
        digest.update(message.model_dump_json().encode())
    return digest.hexdigest()


def _usable(value: str) -> bool:
    return (
        0 < len(value) <= _MAX_IDENTITY
        and value == value.strip()
        and "[redacted]" not in value.lower()
        and value.isprintable()
    )


def normalize_file_path(path: str) -> str | None:
    """Validate an exact slash-delimited repository-relative file selector."""
    if (
        _usable(path)
        and not any(character in path for character in "\\:")
        and all(part not in {"", ".", ".."} for part in path.split("/"))
    ):
        return path
    return None


def _absolute_path(value: str | None) -> _AbsolutePath | None:
    if not value or not _usable(value):
        return None
    windows = value.replace("\\", "/")
    if _DRIVE.match(windows):
        anchor, tail = windows[:2].upper(), windows[3:]
    elif value.startswith("/") and not value.startswith("//"):
        anchor, tail = "/", value[1:]
    else:
        return None
    tail = tail.removesuffix("/")
    if anchor != "/" and any(part.endswith((" ", ".")) for part in tail.split("/")):
        return None
    if tail and normalize_file_path(tail) is None:
        return None
    return _AbsolutePath(anchor, tuple(tail.split("/")) if tail else ())


def _repository(archived: EnrichedConversation) -> str | None:
    recorded, enriched = archived.conversation.repository, archived.provenance.repository
    if recorded and enriched and recorded != enriched:
        return None
    repository = recorded or enriched
    if not repository or not _usable(repository):
        return None
    if (checkout := _absolute_path(repository)) is not None and checkout.parts:
        return repository
    # Require a qualified identity. In particular a project slug or a repository basename
    # cannot identify which checkout is being edited.
    if re.fullmatch(
        r"(?:(?:https?://|ssh://(?:git@)?)[a-zA-Z0-9.-]+/|git@[a-zA-Z0-9.-]+:)"
        r"(?:[a-zA-Z0-9_.-]+/)+[a-zA-Z0-9_.-]+",
        repository,
    ):
        return repository
    return None


def _tool_pairs(
    archived: EnrichedConversation,
) -> Iterator[tuple[_ToolField, _ToolField]]:
    source = archived.conversation.source
    if source not in {Source.CLAUDE_CODE, Source.CODEX}:
        return
    requests, results = {}, {}
    for index, message in enumerate(archived.conversation.messages):
        if message.role not in {Role.ASSISTANT, Role.TOOL}:
            continue
        request = message.role == Role.ASSISTANT
        id_field = "id" if request else "tool_use_id"
        if source == Source.CODEX:
            id_field = "call_id"
        records = requests if request else results
        for tool_index, tool in enumerate(message.tool_activity):
            raw = tool.request if request else tool.result
            if not raw or len(raw) > _MAX_FIELD:
                continue
            payload = _object(raw)
            call_id = payload.get(id_field)
            if not isinstance(call_id, str) or not _usable(call_id):
                continue
            records[call_id] = (
                None if call_id in records else _ToolField(index, tool_index, tool.name, payload)
            )
    for call_id, result in results.items():
        request = requests.get(call_id)
        if (
            request is not None
            and result is not None
            and request.message < result.message
            and request.name == result.name
        ):
            yield request, result


def _arguments(request: _ToolField) -> dict | str | None:
    return request.payload.get("input", request.payload.get("arguments"))


def _output(payload: dict) -> str:
    output = payload.get("output", payload.get("content"))
    if isinstance(output, dict):
        output = output.get("stdout")
    if not isinstance(output, str):
        return ""
    if marker := _CODEX_EXIT.match(output):
        output = re.sub(
            r"\A(?:Original token count: [0-9]+(?:\r?\n))?(?:Final output|Output):\r?\n",
            "",
            output[marker.end() :],
            count=1,
        )
    return output


def _git_arguments(source: Source, request: _ToolField, cwd: _AbsolutePath | None) -> list[str]:
    if cwd is None or request.name != ("Bash" if source == Source.CLAUDE_CODE else "exec_command"):
        return []
    args = _arguments(request)
    if not isinstance(args, dict):
        return []
    if "workdir" in args:
        workdir = args["workdir"]
        if not isinstance(workdir, str) or _absolute_path(workdir) != cwd:
            return []
    command = args.get("command" if source == Source.CLAUDE_CODE else "cmd")
    if not isinstance(command, str) or _UNSAFE_SHELL.search(command):
        return []
    # Parse words for a small command allowlist. No command is executed by this projection.
    try:
        words = shlex.split(command)
    except ValueError:
        return []
    return words[1:] if words and words[0] == "git" else []


def _path_in_checkout(value: str, cwd: _AbsolutePath, root: _AbsolutePath) -> str | None:
    if absolute := _absolute_path(value):
        relative = absolute.relative_to(root)
    elif path := normalize_file_path(value.replace("\\", "/") if cwd.anchor != "/" else value):
        if cwd.anchor != "/" and any(part.endswith((" ", ".")) for part in path.split("/")):
            return None
        prefix = cwd.relative_to(root)
        relative = (*prefix, *path.split("/")) if prefix is not None else None
    else:
        return None
    return normalize_file_path("/".join(relative)) if relative else None


def _edit_paths(source: Source, request: _ToolField, result: _ToolField) -> Iterator[str]:
    args = _arguments(request)
    success = _result_success(result.payload)
    output = _output(result.payload)
    if (
        source == Source.CODEX
        and request.name == "apply_patch"
        and isinstance(args, str)
        and args.startswith(("*** Begin Patch\n", "*** Begin Patch\r\n"))
        and args.rstrip().endswith("\n*** End Patch")
        and success is not False
    ):
        header, _, lines = output.lstrip("\r\n").partition("\n")
        if header.rstrip("\r") != "Success. Updated the following files:":
            return
        confirmed = {line[2:] for line in lines.splitlines() if line[:2] in {"A ", "D ", "M "}}
        for match in _PATCH_PATH.finditer(args):
            if (path := match[1].removesuffix("\r")) in confirmed:
                yield path
    elif (
        source == Source.CLAUDE_CODE
        and request.name in _CLAUDE_EDITS
        and isinstance(args, dict)
        and success is True
    ):
        path = args.get("notebook_path" if request.name == "NotebookEdit" else "file_path")
        if isinstance(path, str) and _usable(path) and _affirms_edit(result.payload, path):
            yield path


def _commit_args(args: list[str]) -> bool:
    # A direct invocation with no option that could suppress an actual commit.
    if not args or args[0] != "commit":
        return False
    options = iter(args[1:])
    for option in options:
        if option in {"-m", "--message"}:
            if next(options, None) is None:
                return False
        elif option not in {"-a", "--all", "--amend", "--no-edit", "--allow-empty", "--no-verify"}:
            return False
    return True


def _tool_relations(
    archived: EnrichedConversation,
) -> Iterator[tuple[str, Node, int, int]]:
    repository = _repository(archived)
    cwd = _absolute_path(archived.conversation.working_directory)
    has_repository = archived.conversation.repository or archived.provenance.repository
    if cwd is None or (has_repository and repository is None):
        return

    source = archived.conversation.source
    roots = set()
    if explicit_root := _absolute_path(repository):
        roots.add(explicit_root)
    patches = []
    commits, known_oids = [], set()
    for request, result in _tool_pairs(archived):
        recorded_cwd = request.payload.get("recorded_cwd")
        if "recorded_cwd" in request.payload and (
            not isinstance(recorded_cwd, str) or _absolute_path(recorded_cwd) != cwd
        ):
            continue
        for path in _edit_paths(source, request, result):
            if recorded_cwd is not None or _absolute_path(path) is not None:
                patches.append((path, result))
        if _result_success(result.payload) is not True:
            continue
        args = _git_arguments(source, request, cwd)
        if not args:
            continue
        output = _output(result.payload)
        if args == ["rev-parse", "--show-toplevel"]:
            # Remove the output newline only. Whitespace in a path is meaningful.
            if root := _absolute_path(output.removesuffix("\n").removesuffix("\r")):
                roots.add(root)
            continue
        # A result can prove an absolute checkout root, but a commit needs its
        # operation's scope as well. A legacy invocation may still have explicit workdir.
        arguments = _arguments(request)
        if recorded_cwd is None and not (isinstance(arguments, dict) and "workdir" in arguments):
            continue
        if args == ["rev-parse", "HEAD"] and _OID.fullmatch(output.strip()):
            known_oids.add(output.strip().lower())
        elif _commit_args(args) and (match := _COMMIT_RESULT.match(output)):
            oid = match[1].lower()
            commits.append((oid, result))
            if _OID.fullmatch(oid):
                known_oids.add(oid)

    if len(roots) != 1:
        return
    (root,) = roots
    if cwd.relative_to(root) is None:
        return
    repository = repository or root.anchor.removesuffix("/") + "/" + "/".join(root.parts)
    for path, result in patches:
        if normalized := _path_in_checkout(path, cwd, root):
            file = Node("file", normalized, normalized, repository)
            yield FILE_EDIT, file, result.message, result.tool

    ordered_oids = sorted(known_oids)
    for oid, result in commits:
        if not _OID.fullmatch(oid):
            start = bisect_left(ordered_oids, oid)
            stop = bisect_left(ordered_oids, oid + "g")
            if stop - start != 1:
                continue
            oid = ordered_oids[start]
        yield COMMIT, Node("commit", oid, oid, repository), result.message, result.tool


def _pr_references(text: str) -> Iterator[Node]:
    if len(text) > _MAX_FIELD:
        return
    for match in _PR.finditer(text):
        host, owner, repo, pull = match.groups()
        if owner in {".", ".."} or repo in {".", ".."}:
            continue
        url = f"https://{host.lower()}/{owner}/{repo}/{pull}"
        if _usable(url):
            yield Node("pr", url, url)


def project_evidence(archived: EnrichedConversation) -> Iterator[EvidenceEdge]:
    """Project candidates; the index resolves continuation targets in the same project."""
    project = project_of(archived)
    document = archived.document_id
    if project is None or not _usable(document):
        return
    conversation = archived.conversation
    snapshot = snapshot_of(archived)
    origin = Node("session", document, document)

    def edge(relation: str, target: Node, index: int, tool: int | None, field: str) -> EvidenceEdge:
        time = conversation.messages[index].sent_at or conversation.started_at
        return EvidenceEdge(
            project,
            origin,
            target,
            relation,
            document,
            index,
            tool,
            field,
            time.astimezone(UTC).isoformat(timespec="microseconds"),
            snapshot,
        )

    for index, message in enumerate(conversation.messages):
        if (
            message.role == Role.USER
            and len(message.text) <= _MAX_FIELD
            and (match := _CONTINUATION.match(message.text))
        ):
            target = match[1] or match[2]
            if _usable(target) and target != document:
                yield edge(CONTINUATION, Node("session", target, target), index, None, "text")
        if message.role in {Role.USER, Role.ASSISTANT}:
            for target in _pr_references(message.text):
                yield edge(PR_REFERENCE, target, index, None, "text")
        if message.role == Role.TOOL:
            for tool_index, tool in enumerate(message.tool_activity):
                if tool.result and len(tool.result) <= _MAX_FIELD:
                    data = _object(tool.result)
                    if _result_success(data) is not False:
                        for target in _pr_references(_output(data)):
                            yield edge(PR_REFERENCE, target, index, tool_index, "tool_result")
    for relation, target, index, tool in _tool_relations(archived):
        yield edge(relation, target, index, tool, "tool_result")
