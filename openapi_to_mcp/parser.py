"""Parser for OpenAPI 3.x and Swagger 2.0 specifications."""

import re
import json
from typing import Any, Dict, List, Optional
import httpx
import yaml
from pydantic import BaseModel, Field


class ParsedTool(BaseModel):
    """Represents an executable MCP tool extracted from an OpenAPI endpoint."""
    name: str
    method: str
    path: str
    summary: str
    description: str
    tags: List[str] = Field(default_factory=list)
    parameters_schema: Dict[str, Any]
    path_param_names: List[str] = Field(default_factory=list)
    query_param_names: List[str] = Field(default_factory=list)
    body_param_name: Optional[str] = None


class OpenAPIParser:
    """Parses OpenAPI 3.x / Swagger 2.0 specs into MCP tool schemas."""

    def __init__(self, spec_data: Dict[str, Any], base_url_override: Optional[str] = None):
        self.spec = spec_data
        self.base_url = base_url_override or self._extract_base_url()

    @classmethod
    def from_source(cls, source: str, base_url_override: Optional[str] = None) -> "OpenAPIParser":
        """Load from URL or local file path (supports JSON and YAML)."""
        if source.startswith("http://") or source.startswith("https://"):
            resp = httpx.get(source, timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
            text = resp.text
        else:
            with open(source, "r", encoding="utf-8") as f:
                text = f.read()

        try:
            data = json.loads(text)
        except Exception:
            data = yaml.safe_load(text)

        return cls(data, base_url_override)

    def _extract_base_url(self) -> str:
        # OpenAPI 3.x servers
        if "servers" in self.spec and self.spec["servers"]:
            return self.spec["servers"][0].get("url", "http://localhost")

        # Swagger 2.0 schemes + host + basePath
        schemes = self.spec.get("schemes", ["https"])
        scheme = schemes[0] if schemes else "https"
        host = self.spec.get("host", "localhost")
        base_path = self.spec.get("basePath", "")
        return f"{scheme}://{host}{base_path}".rstrip("/")

    @staticmethod
    def sanitize_tool_name(name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        return cleaned or "unnamed_tool"

    def parse_tools(
        self,
        include_tags: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
    ) -> List[ParsedTool]:
        tools: List[ParsedTool] = []
        paths = self.spec.get("paths", {})
        allowed_methods_set = set(m.lower() for m in allowed_methods) if allowed_methods else None

        for path, path_item in paths.items():
            if exclude_paths and any(ex in path for ex in exclude_paths):
                continue

            for method, op in path_item.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch", "options", "head"):
                    continue
                if allowed_methods_set and method.lower() not in allowed_methods_set:
                    continue

                tags = op.get("tags", [])
                if include_tags and not any(t in include_tags for t in tags):
                    continue

                operation_id = op.get("operationId")
                if operation_id:
                    tool_name = self.sanitize_tool_name(operation_id)
                else:
                    path_clean = re.sub(r"[{}]", "", path).replace("/", "_")
                    tool_name = self.sanitize_tool_name(f"{method.lower()}_{path_clean}")

                summary = op.get("summary") or f"{method.upper()} {path}"
                desc = op.get("description") or summary

                # Build JSON Schema properties
                properties: Dict[str, Any] = {}
                required_props: List[str] = []
                path_params: List[str] = []
                query_params: List[str] = []
                body_param: Optional[str] = None

                # Process parameters (path, query, header)
                parameters = op.get("parameters", []) + path_item.get("parameters", [])
                for param in parameters:
                    name = param.get("name")
                    if not name:
                        continue
                    in_location = param.get("in")
                    schema = param.get("schema", {"type": param.get("type", "string")})
                    description = param.get("description", "")

                    if in_location == "path":
                        path_params.append(name)
                        properties[name] = {**schema, "description": f"(Path param) {description}".strip()}
                        if param.get("required", True):
                            required_props.append(name)
                    elif in_location == "query":
                        query_params.append(name)
                        properties[name] = {**schema, "description": f"(Query param) {description}".strip()}
                        if param.get("required", False):
                            required_props.append(name)

                # Process requestBody (OpenAPI 3.x)
                if "requestBody" in op:
                    content = op["requestBody"].get("content", {})
                    json_body = content.get("application/json") or content.get("*/*")
                    if json_body and "schema" in json_body:
                        body_param = "request_body"
                        body_schema = json_body["schema"]
                        properties["request_body"] = {
                            **body_schema,
                            "description": op["requestBody"].get("description", "JSON request payload"),
                        }
                        if op["requestBody"].get("required", False):
                            required_props.append("request_body")

                tool_schema = {
                    "type": "object",
                    "properties": properties,
                    "required": list(set(required_props)),
                }

                tools.append(
                    ParsedTool(
                        name=tool_name,
                        method=method.upper(),
                        path=path,
                        summary=summary,
                        description=desc,
                        tags=tags,
                        parameters_schema=tool_schema,
                        path_param_names=path_params,
                        query_param_names=query_params,
                        body_param_name=body_param,
                    )
                )

        return tools
