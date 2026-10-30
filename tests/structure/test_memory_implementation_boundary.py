"""Production consumers must not reach the concrete memory implementation."""

import ast
from importlib.util import resolve_name
from pathlib import Path

PREFIX = "engineering_memory.memory.hindsight"


def violations(sources, packages=()):
    graph = {}
    for module, text in sources.items():
        edges = set()
        package = module if module in packages else module.rpartition(".")[0]
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                edges.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                name = node.module or ""
                if node.level:
                    name = resolve_name("." * node.level + name, package)
                edges.add(name)
                edges.update(name + "." + alias.name for alias in node.names)
            elif (
                isinstance(node, ast.Call)
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and (
                    (isinstance(node.func, ast.Name) and node.func.id == "__import__")
                    or (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")
                )
            ):
                edges.add(node.args[0].value)
        # Importing a submodule also executes its package initializers.
        graph[module] = edges | {
            ".".join(edge.split(".")[:index])
            for edge in edges
            for index in range(1, len(edge.split(".")))
        }

    def reaches_adapter(module, seen):
        if module == PREFIX or module.startswith(PREFIX + "."):
            return True
        if module in seen:
            return False
        seen.add(module)
        return any(reaches_adapter(edge, seen) for edge in graph.get(module, ()))

    return sorted(
        module
        for module in graph
        if not module.startswith(PREFIX) and reaches_adapter(module, set())
    )


def test_guard_rejects_direct_relative_and_indirect_imports():
    sources = {
        "engineering_memory.pipeline": "from engineering_memory.bridge import Store",
        "engineering_memory.bridge": "from .memory.hindsight.store import Store",
        "engineering_memory.memory.hindsight.store": "",
    }
    assert set(violations(sources)) == {"engineering_memory.pipeline", "engineering_memory.bridge"}
    assert violations({"engineering_memory.access": "import engineering_memory.memory.hindsight"})
    assert violations(
        {"engineering_memory.access": "from engineering_memory.memory import hindsight"}
    )


def test_guard_allows_interface_and_adapter_dependencies():
    assert (
        violations(
            {
                "engineering_memory.access": (
                    "from engineering_memory.memory.interface import MemoryStore"
                ),
                PREFIX + ".store": "from .serialization import item_for",
                PREFIX + ".serialization": "",
            }
        )
        == []
    )


def test_no_production_consumer_reaches_adapter():
    root = Path(__file__).resolve().parents[2] / "src"
    sources = {}
    packages = set()
    for file in (root / "engineering_memory").rglob("*.py"):
        parts = list(file.relative_to(root).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
            packages.add(".".join(parts))
        sources[".".join(parts)] = file.read_text(encoding="utf-8")
    assert violations(sources, packages) == []
