"""Model Context Protocol (MCP) stdio JSON-RPC server implementation."""

import sys
import json
import asyncio
from typing import Any, Dict, List, Optional
from openapi_to_mcp.parser import OpenAPIParser, ParsedTool
from openapi_to_mcp.client import APIClient


class MCPServer:
    """Standard MCP stdio server exposing OpenAPI endpoints as native agent tools."""

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(
        self,
        parser: OpenAPIParser,
        client: APIClient,
        tools: List[ParsedTool],
        server_name: str = "openapi-to-mcp",
        server_version: str = "0.1.0",
    ):
        self.parser = parser
        self.client = client
        self.tools_map: Dict[str, ParsedTool] = {t.name: t for t in tools}
        self.server_name = server_name
        self.server_version = server_version

    def _format_tools_list(self) -> List[Dict[str, Any]]:
        result = []
        for tool in self.tools_map.values():
            result.append({
                "name": tool.name,
                "description": f"[{tool.method}] {tool.summary} - {tool.description}".strip(),
                "inputSchema": tool.parameters_schema,
            })
        return result

    async def handle_request(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        # 1. Initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.server_version,
                    },
                },
            }

        # 2. Ping
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        # 3. Initialized Notification (no response needed)
        elif method == "notifications/initialized":
            return None

        # 4. List Tools
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self._format_tools_list(),
                },
            }

        # 5. Call Tool
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tools_map:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found",
                    },
                }

            tool = self.tools_map[tool_name]
            call_res = await self.client.execute_tool(tool, arguments)

            output_text = json.dumps(call_res.get("data"), indent=2) if isinstance(call_res.get("data"), (dict, list)) else str(call_res.get("data") or call_res.get("error"))

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": output_text,
                        }
                    ],
                    "isError": call_res.get("is_error", False),
                },
            }

        # Unknown method
        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not implemented",
                },
            }
        return None

    async def run_stdio(self):
        """Asynchronous event loop reading lines from standard input and responding to stdout."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break
            raw_text = line.decode("utf-8").strip()
            if not raw_text:
                continue

            try:
                msg = json.loads(raw_text)
                response = await self.handle_request(msg)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error or exception: {str(e)}"},
                }
                sys.stdout.write(json.dumps(err_response) + "\n")
                sys.stdout.flush()
