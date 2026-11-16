"""Unit tests for openapi-to-mcp parser and MCP server protocol."""

import asyncio
import pytest
from pathlib import Path
from openapi_to_mcp.parser import OpenAPIParser
from openapi_to_mcp.client import APIClient
from openapi_to_mcp.server import MCPServer


@pytest.fixture
def sample_spec_path() -> str:
    path = Path(__file__).parent.parent / "examples" / "sample_petstore_spec.json"
    return str(path)


def test_parser_extracts_tools(sample_spec_path):
    parser = OpenAPIParser.from_source(sample_spec_path)
    tools = parser.parse_tools()

    assert len(tools) == 4
    tool_names = [t.name for t in tools]
    assert "getpetbyid" in tool_names
    assert "deletepet" in tool_names
    assert "findpetsbystatus" in tool_names
    assert "placeorder" in tool_names


def test_parser_filters_by_tag(sample_spec_path):
    parser = OpenAPIParser.from_source(sample_spec_path)
    tools = parser.parse_tools(include_tags=["store"])

    assert len(tools) == 1
    assert tools[0].name == "placeorder"


def test_parser_filters_by_method(sample_spec_path):
    parser = OpenAPIParser.from_source(sample_spec_path)
    tools = parser.parse_tools(allowed_methods=["GET"])

    assert len(tools) == 2
    for t in tools:
        assert t.method == "GET"


def test_mcp_server_protocol(sample_spec_path):
    async def _test():
        parser = OpenAPIParser.from_source(sample_spec_path)
        tools = parser.parse_tools()
        client = APIClient(base_url=parser.base_url)
        server = MCPServer(parser=parser, client=client, tools=tools)

        # 1. Test initialize
        init_res = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert init_res["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in init_res["result"]["capabilities"]

        # 2. Test ping
        ping_res = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "ping",
        })
        assert ping_res["result"] == {}

        # 3. Test tools/list
        list_res = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
        })
        tools_returned = list_res["result"]["tools"]
        assert len(tools_returned) == 4
        assert any(t["name"] == "getpetbyid" for t in tools_returned)

    asyncio.run(_test())
