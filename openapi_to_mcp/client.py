"""HTTP execution client for dispatching OpenAPI tool calls."""

from typing import Any, Dict, Optional
import httpx
from openapi_to_mcp.parser import ParsedTool


class APIClient:
    """Executes HTTP requests based on ParsedTool definitions."""

    def __init__(
        self,
        base_url: str,
        default_headers: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = default_headers or {}
        self.timeout = timeout_seconds

    async def execute_tool(self, tool: ParsedTool, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves parameters and dispatches the HTTP call asynchronously."""
        # 1. Substitute path parameters
        url_path = tool.path
        for param_name in tool.path_param_names:
            if param_name in arguments:
                url_path = url_path.replace(f"{{{param_name}}}", str(arguments[param_name]))

        target_url = f"{self.base_url}{url_path}"

        # 2. Extract query parameters
        query_params = {}
        for param_name in tool.query_param_names:
            if param_name in arguments:
                query_params[param_name] = arguments[param_name]

        # 3. Extract request body
        json_body = None
        if tool.body_param_name and tool.body_param_name in arguments:
            json_body = arguments[tool.body_param_name]

        # 4. Dispatch request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=tool.method,
                    url=target_url,
                    params=query_params or None,
                    json=json_body,
                    headers=self.headers,
                )

                try:
                    data = response.json()
                except Exception:
                    data = response.text

                return {
                    "status_code": response.status_code,
                    "url": str(response.url),
                    "data": data,
                    "is_error": response.is_error,
                }
            except httpx.RequestError as exc:
                return {
                    "status_code": 0,
                    "url": target_url,
                    "data": None,
                    "is_error": True,
                    "error": f"HTTP Request failed: {str(exc)}",
                }
