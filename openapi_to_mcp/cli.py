"""Command-line interface for openapi-to-mcp."""

import argparse
import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from openapi_to_mcp.parser import OpenAPIParser
from openapi_to_mcp.client import APIClient
from openapi_to_mcp.server import MCPServer

console = Console(stderr=True)  # stderr so stdout remains clean for MCP JSON-RPC


def parse_headers(header_args):
    headers = {}
    if header_args:
        for h in header_args:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()
    return headers


def cmd_inspect(args):
    """Inspect and list tools parsed from OpenAPI specification."""
    parser = OpenAPIParser.from_source(args.spec, base_url_override=args.base_url)
    include_tags = args.include_tags.split(",") if args.include_tags else None
    allowed_methods = args.methods.split(",") if args.methods else None

    tools = parser.parse_tools(include_tags=include_tags, allowed_methods=allowed_methods)

    console.print(Panel.fit(
        f"[bold cyan]OpenAPI Specification:[/bold cyan] {args.spec}\n"
        f"[bold cyan]Base URL:[/bold cyan] {parser.base_url}\n"
        f"[bold green]Parsed Tools:[/bold green] {len(tools)} endpoint(s) ready for MCP agents",
        title="openapi-to-mcp Inspector",
    ))

    table = Table(title="Generated MCP Tools")
    table.add_column("MCP Tool Name", style="bold cyan")
    table.add_column("Method", style="magenta")
    table.add_column("Endpoint Path", style="dim")
    table.add_column("Parameters", style="yellow")
    table.add_column("Summary")

    for t in tools:
        param_list = list(t.parameters_schema.get("properties", {}).keys())
        table.add_row(
            t.name,
            t.method,
            t.path,
            ", ".join(param_list) if param_list else "(none)",
            t.summary[:60] + ("..." if len(t.summary) > 60 else ""),
        )

    console.print(table)


def cmd_serve(args):
    """Start standard stdio MCP server."""
    parser = OpenAPIParser.from_source(args.spec, base_url_override=args.base_url)
    include_tags = args.include_tags.split(",") if args.include_tags else None
    allowed_methods = args.methods.split(",") if args.methods else None
    headers = parse_headers(args.header)

    tools = parser.parse_tools(include_tags=include_tags, allowed_methods=allowed_methods)
    client = APIClient(base_url=parser.base_url, default_headers=headers)
    server = MCPServer(parser=parser, client=client, tools=tools)

    console.print(f"[green]Starting MCP stdio server with {len(tools)} tools...[/green]")
    asyncio.run(server.run_stdio())


def main():
    parser = argparse.ArgumentParser(description="Convert any OpenAPI/Swagger REST API into an MCP server")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect and preview tools generated from OpenAPI spec")
    p_inspect.add_argument("--spec", "-s", required=True, help="Path or URL to OpenAPI/Swagger JSON or YAML")
    p_inspect.add_argument("--base-url", "-u", help="Override API base URL")
    p_inspect.add_argument("--include-tags", help="Comma-separated OpenAPI tags to include")
    p_inspect.add_argument("--methods", help="Comma-separated HTTP methods to include (e.g. GET,POST)")
    p_inspect.set_defaults(func=cmd_inspect)

    # Serve
    p_serve = subparsers.add_parser("serve", help="Run stdio MCP server for Claude Desktop, Cursor, or agents")
    p_serve.add_argument("--spec", "-s", required=True, help="Path or URL to OpenAPI/Swagger JSON or YAML")
    p_serve.add_argument("--base-url", "-u", help="Override API base URL")
    p_serve.add_argument("--header", "-H", action="append", help="HTTP header (e.g. 'Authorization: Bearer <token>')")
    p_serve.add_argument("--include-tags", help="Comma-separated OpenAPI tags to include")
    p_serve.add_argument("--methods", help="Comma-separated HTTP methods to include")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
