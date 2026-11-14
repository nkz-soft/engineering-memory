"""SDK client handshake and two-tool retrieval through an actual subprocess."""

import json
import os
import sys

import anyio
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from tests.contracts import conversations as synth


def test_stdio_consumer(tmp_path):
    archive = LocalRawArchive(tmp_path / "archive")
    enriched = synth.enrich(synth.conversation_using_every_field())
    archive.store(
        enriched, OriginalPayload(content=b"ORIGINAL_SECRET_SENTINEL", media_type="text/plain")
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("ENGINEERING_MEMORY_")}
    env.update(
        ENGINEERING_MEMORY_ARCHIVE_ROOT=str(tmp_path / "archive"),
        ENGINEERING_MEMORY_HINDSIGHT__BASE_URL="http://127.0.0.1:1",
    )
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from engineering_memory.cli import main; main()", "serve"],
        env=env,
        cwd=str(tmp_path),
    )

    async def scenario():
        with anyio.fail_after(30):
            async with Client(parameters, mode="legacy") as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "search_memory",
                    "get_conversation",
                    "get_project_model",
                    "reflect",
                    "deep_recall",
                }
                assert all(tool.annotations.read_only_hint for tool in tools.tools)
                for tool in tools.tools:
                    assert tool.input_schema["type"] == "object"
                page = await client.call_tool(
                    "get_conversation", {"document_id": enriched.document_id, "page_size": 1}
                )
                assert not page.is_error
                data = page.structured_content
                assert data["document_id"] == enriched.document_id
                assert (
                    data["messages"]
                    == enriched.conversation.model_dump(mode="json")["messages"][:1]
                )
                assert data["next_offset"] == 1
                assert "ORIGINAL_SECRET_SENTINEL" not in page.model_dump_json()
                invalid = await client.call_tool(
                    "get_conversation", {"document_id": "PRIVATE/../secret"}
                )
                assert invalid.is_error
                assert "PRIVATE" not in invalid.model_dump_json()
                invalid_query = await client.call_tool(
                    "search_memory", {"query": {"PRIVATE": "SECRET"}}
                )
                assert invalid_query.is_error
                assert "PRIVATE" not in invalid_query.model_dump_json()
                failure = await client.call_tool("search_memory", {"query": "irrelevant"})
                assert failure.is_error
                assert "unavailable" in json.dumps(failure.model_dump(mode="json"))

    anyio.run(scenario)


def test_missing_required_argument_never_echoes_other_inputs(tmp_path):
    from unittest.mock import Mock

    from engineering_memory.access.server import create_server
    from engineering_memory.access.service import MemoryAccess

    async def scenario():
        async with Client(create_server(MemoryAccess(Mock(), Mock())), mode="legacy") as client:
            result = await client.call_tool("search_memory", {"tags": ["PRIVATE_SENTINEL"]})
            assert result.is_error
            assert "PRIVATE_SENTINEL" not in result.model_dump_json()

    anyio.run(scenario)


def test_raw_json_strings_are_not_reinterpreted():
    from unittest.mock import Mock

    from engineering_memory.access.server import create_server
    from engineering_memory.access.service import MemoryAccess

    memory, archive = Mock(), Mock()
    memory.recall.return_value = ()

    async def scenario():
        async with Client(create_server(MemoryAccess(memory, archive)), mode="legacy") as client:
            result = await client.call_tool("search_memory", {"query": "null"})
            assert not result.is_error and result.structured_content == {"results": []}
            assert memory.recall.call_args.args[0] == "null"
            memory.reset_mock()
            for arguments in [
                {"query": "x", "tags": "null"},
                {"query": "x", "tags": None},
                {"query": "x", "extra": "PRIVATE_SENTINEL"},
            ]:
                result = await client.call_tool("search_memory", arguments)
                assert result.is_error and "PRIVATE_SENTINEL" not in result.model_dump_json()
            memory.recall.assert_not_called()

    anyio.run(scenario)
