# `openapi-to-mcp` ⚡

[![CI](https://github.com/driasim/openapi-to-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/driasim/openapi-to-mcp/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Instantly convert any OpenAPI 3.x or Swagger 2.0 REST API into a Model Context Protocol (MCP) server for Claude Desktop, Cursor, Antigravity, and AI Agents.**

Stop writing manual MCP boilerplate for every REST endpoint. With `openapi-to-mcp`, point to any local `swagger.json` or live API documentation URL, and expose your service's endpoints as executable AI tools in seconds.

---

## 🚀 Why Clone This?

* 🔄 **Zero-Boilerplate MCP:** Takes any REST API (Stripe, GitHub, internal corporate services, Jira, Shopify) and auto-generates MCP tool definitions with parameter schemas.
* 🖥️ **Drop-in for Claude Desktop & Cursor:** Fully compliant with standard MCP JSON-RPC 2.0 over `stdio`.
* 🔑 **Authentication & Custom Headers:** Injects Bearer tokens, API keys, or custom headers on all dispatched calls.
* 🎯 **Smart Filtering:** Filter tools by OpenAPI tags or HTTP methods so your LLM context isn't overwhelmed with hundreds of unused endpoints.
* 📦 **Zero-Config Inspector:** Preview generated tools in formatted terminal tables before launching the server.

---

## 📦 Quickstart

### 1. Installation

```bash
git clone https://github.com/driasim/openapi-to-mcp.git
cd openapi-to-mcp
pip install -e .
```

### 2. Preview Generated Tools (`inspect`)

```bash
openapi-to-mcp inspect --spec ./examples/sample_petstore_spec.json
```

Or directly from any live URL:

```bash
openapi-to-mcp inspect --spec https://petstore.swagger.io/v2/swagger.json
```

### 3. Run the MCP Server (`serve`)

```bash
openapi-to-mcp serve \
  --spec https://api.mycompany.com/openapi.json \
  --header "Authorization: Bearer srv_live_secret123"
```

---

## 🤖 Connect to Claude Desktop

Add this to your `claude_desktop_config.json`:

* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-internal-api": {
      "command": "python",
      "args": [
        "-m",
        "openapi_to_mcp.cli",
        "serve",
        "--spec",
        "https://api.mycompany.internal/openapi.json",
        "--header",
        "Authorization: Bearer YOUR_API_TOKEN"
      ]
    }
  }
}
```

Now Claude Desktop can natively query, call, and manage your API endpoints!

---

## 🎯 Filtering Tools for Large APIs

If an OpenAPI specification has 200+ endpoints, feeding all of them into an LLM degrades tool-selection accuracy. Filter down to the exact subset needed:

```bash
# Only expose tools tagged 'billing' and 'invoices'
openapi-to-mcp serve \
  --spec ./swagger.json \
  --include-tags billing,invoices

# Only expose safe read-only methods
openapi-to-mcp serve \
  --spec ./swagger.json \
  --methods GET
```

---

## 🧪 Running Tests

```bash
pytest -v tests/
```

---

## 📄 License

MIT © Ibrahim Aliyu Saddique (`@driasim`)
