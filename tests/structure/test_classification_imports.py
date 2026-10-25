"""The classifier reaches neither Hindsight, nor the network, nor storage (Principle IV).

`classification` is the second package to hold both an interface and its implementation: #9
declared the boundary in `classifier.py`, and #12 fills the rest of the package with the alias
rules behind it. The allowlist is the interface's, widened by three things the rules need — `re`
and `tomllib` from the standard library, and the logging of #6 for the two records the loader emits
(specs/010-project-classifier/research.md R11).

That last one carries an obligation this file cannot express, and does not need to: the logging
import must stay **inside** the loader's function body. `hermes_memory.observability` pulls
OpenTelemetry, which pulls `socket`, and `test_boundary_interfaces.py` imports this package in a
fresh interpreter and fails on exactly that. So the module-scope rule is enforced there, by a test
that was already standing, and what is enforced here is the narrower question of which names may
appear at all.

A model SDK and an HTTP client are forbidden for a second reason beyond Principle IV: §21 puts
model-based classification out of scope, and CH-6 says the MVP composes no such classifier. A
dependency that could call one has no business in this package yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

from tests.structure.test_boundary_interfaces import FORBIDDEN_AT_RUNTIME, imported_roots

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "src" / "hermes_memory" / "classification"

ALLOWED_THIRD_PARTY = frozenset({"pydantic", "structlog"})

ALLOWED_INTERNAL = (
    "hermes_memory.errors",
    "hermes_memory.normalization",
    "hermes_memory.observability",
    "hermes_memory.classification",
)

MODEL_CLIENTS = (
    "openai",
    "anthropic",
    "litellm",
    "langchain",
    "transformers",
    "ollama",
)
"""No classifier here asks a model (§21, CH-6). Named separately so the failure says why."""


def _is_forbidden(imported: str) -> bool:
    return any(
        imported == forbidden or imported.startswith(f"{forbidden}.")
        for forbidden in (*FORBIDDEN_AT_RUNTIME, *MODEL_CLIENTS)
    )


def _is_allowed(imported: str) -> bool:
    if _is_forbidden(imported):
        return False
    root = imported.split(".")[0]
    return (
        root in sys.stdlib_module_names
        or root in ALLOWED_THIRD_PARTY
        or any(
            imported == allowed or imported.startswith(f"{allowed}.")
            for allowed in ALLOWED_INTERNAL
        )
    )


def _offenders(package: Path) -> list[str]:
    return [
        f"{source.name}: {imported}"
        for source in sorted(package.rglob("*.py"))
        for imported in sorted(imported_roots(source))
        if not _is_allowed(imported)
    ]


def test_the_classifier_imports_only_what_it_may() -> None:
    offenders = _offenders(PACKAGE)

    assert not offenders, (
        f"These imports are outside the allowlist: {offenders}. A classifier answers from rules "
        "held in memory; it reaches neither Hindsight, nor the network, nor storage "
        "(Principle IV), and it asks no model (§21)."
    )


def test_the_guard_still_bites(tmp_path: Path) -> None:
    (tmp_path / "leak.py").write_text(
        "import httpx\nimport openai\nfrom hermes_memory.settings import Settings\n",
        encoding="utf-8",
    )

    assert _offenders(tmp_path) == [
        "leak.py: hermes_memory.settings",
        "leak.py: httpx",
        "leak.py: openai",
    ]
